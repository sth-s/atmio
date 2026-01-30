import os
import time
import logging
import re
import json
from typing import Any, Optional

from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnableSerializable
from langchain_core.messages import SystemMessage, HumanMessage
from openai import RateLimitError

logger = logging.getLogger("atmio.openrouter")


def get_dev_mode() -> bool:
    return os.getenv("DEV_MODE", "false").lower() == "true"


class RateLimitedOpenRouterLLM(RunnableSerializable):
    model: str = ""
    llm: Any = None
    dev_mode: bool = False
    base_wait: int = 5
    max_wait: int = 120
    max_retries: int = 10
    
    def __init__(self, model: Optional[str] = None, temperature: float = 0, **kwargs):
        super().__init__(**kwargs)
        self.model = model or os.getenv("OPENROUTER_MODEL", "qwen/qwen-2.5-72b-instruct")
        self.llm = ChatOpenAI(
            model=self.model,
            openai_api_key=os.getenv("OPENROUTER_API_KEY"),
            openai_api_base="https://openrouter.ai/api/v1",
            temperature=temperature
        )
        self.dev_mode = get_dev_mode()

    def _parse_retry_after(self, error: Exception) -> int:
        error_str = str(error)
        match = re.search(r"try again in (\d+\.?\d*)s", error_str.lower())
        if match:
            return int(float(match.group(1))) + 1
        match = re.search(r"retry.?after[:\s]+(\d+)", error_str.lower())
        if match:
            return int(match.group(1))
        return self.base_wait

    def _log_request(self, messages: Any) -> None:
        if not self.dev_mode:
            return
        logger.debug(f"[OpenRouter REQUEST] Model: {self.model}")
        if hasattr(messages, '__iter__') and not isinstance(messages, str):
            for i, msg in enumerate(messages):
                content = getattr(msg, 'content', str(msg))[:500]
                logger.debug(f"  Message[{i}]: {content}")

    def _log_response(self, response: Any) -> None:
        if not self.dev_mode:
            return
        content = getattr(response, 'content', str(response))[:1000]
        logger.debug(f"[OpenRouter RESPONSE]: {content}")

    def _retry_loop(self, fn, *args, **kwargs) -> Any:
        attempt = 0
        wait_time = self.base_wait
        
        while attempt < self.max_retries:
            try:
                return fn(*args, **kwargs)
            except RateLimitError as e:
                attempt += 1
                wait_time = min(self._parse_retry_after(e), self.max_wait)
                logger.warning(f"OpenRouter rate limit hit (attempt {attempt}/{self.max_retries}). Waiting {wait_time}s...")
                time.sleep(wait_time)
                wait_time = min(wait_time * 2, self.max_wait)
            except Exception as e:
                error_str = str(e).lower()
                is_429 = "429" in error_str or "too many requests" in error_str
                is_rate_limit = is_429 and "rate" in error_str
                
                if is_rate_limit:
                    attempt += 1
                    wait_time = min(self._parse_retry_after(e), self.max_wait)
                    logger.warning(f"Rate limit detected (attempt {attempt}/{self.max_retries}). Waiting {wait_time}s...")
                    time.sleep(wait_time)
                    wait_time = min(wait_time * 2, self.max_wait)
                else:
                    raise
        
        raise RuntimeError(f"Max retries ({self.max_retries}) exceeded for OpenRouter API")

    def invoke(self, input: Any, config: Optional[dict] = None, **kwargs) -> Any:
        self._log_request(input)
        response = self._retry_loop(self.llm.invoke, input, config=config, **kwargs)
        self._log_response(response)
        return response

    def with_structured_output(self, schema_class: Any) -> "StructuredOutputWrapper":
        return StructuredOutputWrapper(self, schema_class)
    
    @property
    def InputType(self) -> Any:
        return self.llm.InputType
    
    @property
    def OutputType(self) -> Any:
        return self.llm.OutputType


class StructuredOutputWrapper(RunnableSerializable):
    client: Any = None
    schema_class: Any = None
    use_native: bool = True
    structured_llm: Any = None
    
    def __init__(self, client: RateLimitedOpenRouterLLM, schema_class: Any, **kwargs):
        super().__init__(**kwargs)
        self.client = client
        self.schema_class = schema_class
        self.use_native = True
        try:
            self.structured_llm = client.llm.with_structured_output(schema_class)
        except Exception:
            self.use_native = False
            self.structured_llm = None

    def _extract_json(self, text: str) -> dict:
        text = text.strip()
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
        if json_match:
            text = json_match.group(1).strip()
        
        brace_start = text.find('{')
        brace_end = text.rfind('}')
        if brace_start != -1 and brace_end != -1:
            text = text[brace_start:brace_end + 1]
        
        return json.loads(text)

    def _get_schema_prompt(self) -> str:
        schema = self.schema_class.model_json_schema()
        return f"Respond ONLY with valid JSON matching this schema:\n{json.dumps(schema, indent=2)}"

    def _fallback_invoke(self, input: Any, config: Optional[dict] = None, **kwargs) -> Any:
        if isinstance(input, dict):
            messages = []
            for key, value in input.items():
                messages.append(HumanMessage(content=f"{key}: {value}"))
            messages.insert(0, SystemMessage(content=self._get_schema_prompt()))
        elif isinstance(input, list):
            messages = list(input)
            messages.insert(0, SystemMessage(content=self._get_schema_prompt()))
        elif isinstance(input, str):
            messages = [
                SystemMessage(content=self._get_schema_prompt()),
                HumanMessage(content=input)
            ]
        else:
            messages = [
                SystemMessage(content=self._get_schema_prompt()),
                HumanMessage(content=str(input))
            ]
        
        response = self.client.invoke(messages, config=config, **kwargs)
        json_data = self._extract_json(response.content)
        return self.schema_class(**json_data)

    def invoke(self, input: Any, config: Optional[dict] = None, **kwargs) -> Any:
        self.client._log_request(input)
        
        if self.use_native and self.structured_llm:
            def call_structured():
                return self.structured_llm.invoke(input, config=config, **kwargs)
            
            try:
                response = self.client._retry_loop(call_structured)
                if self.client.dev_mode:
                    logger.debug(f"[OpenRouter STRUCTURED RESPONSE]: {response}")
                return response
            except Exception as e:
                if "invalid" in str(e).lower() and "schema" in str(e).lower():
                    logger.info("Structured output not supported, falling back to JSON parsing")
                    self.use_native = False
                else:
                    raise
        
        def call_fallback():
            return self._fallback_invoke(input, config=config, **kwargs)
        
        response = self.client._retry_loop(call_fallback)
        if self.client.dev_mode:
            logger.debug(f"[OpenRouter FALLBACK RESPONSE]: {response}")
        return response
    
    @property
    def InputType(self) -> Any:
        return Any
    
    @property
    def OutputType(self) -> Any:
        return self.schema_class
