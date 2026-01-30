import os
import subprocess
import json
import logging
import re
from typing import Any, Optional

from langchain_core.runnables import RunnableSerializable
from langchain_core.messages import BaseMessage, AIMessage

logger = logging.getLogger("atmio.gemini")


def get_dev_mode() -> bool:
    return os.getenv("DEV_MODE", "false").lower() == "true"


class GeminiCLI(RunnableSerializable):
    dev_mode: bool = False
    timeout: int = 90
    
    def __init__(self, timeout: int = 90, **kwargs):
        super().__init__(**kwargs)
        self.dev_mode = get_dev_mode()
        self.timeout = timeout

    def _extract_prompt(self, input: Any) -> str:
        if isinstance(input, str):
            return input
        elif isinstance(input, list):
            parts = []
            for msg in input:
                if hasattr(msg, 'content'):
                    parts.append(msg.content)
                else:
                    parts.append(str(msg))
            return "\n".join(parts)
        elif isinstance(input, dict):
            parts = []
            for key, value in input.items():
                parts.append(f"{key}: {value}")
            return "\n".join(parts)
        else:
            return str(input)

    def _call_gemini(self, prompt: str) -> str:
        if self.dev_mode:
            logger.debug(f"[Gemini CLI REQUEST]: {prompt[:500]}")
        
        env = os.environ.copy()
        
        try:
            logger.info(f"Calling Gemini CLI (prompt: {len(prompt)} chars)")
            
            escaped_prompt = prompt.replace("'", "'\"'\"'")
            cmd = f"echo '{escaped_prompt}' | gemini -o json"
            
            logger.info(f"Executing command: {cmd[:200]}...")
            
            result = subprocess.run(
                cmd,
                shell=True,
                executable="/bin/bash",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=self.timeout,
                cwd=os.getcwd(),
                env=env
            )
            
            logger.info(f"Gemini CLI returned with code: {result.returncode}")
            
            if result.returncode != 0:
                logger.error(f"Gemini CLI error: {result.stderr}")
                raise RuntimeError(f"Gemini CLI failed: {result.stderr}")
            
            try:
                data = json.loads(result.stdout)
                response = data.get("response", "")
            except json.JSONDecodeError:
                response = result.stdout.strip()
            
            if self.dev_mode:
                logger.debug(f"[Gemini CLI RESPONSE]: {response[:1000]}")
            
            return response
            
        except subprocess.TimeoutExpired:
            logger.error(f"Gemini CLI timeout after {self.timeout}s")
            raise RuntimeError(f"Gemini CLI timeout after {self.timeout}s")

    def invoke(self, input: Any, config: Optional[dict] = None, **kwargs) -> AIMessage:
        prompt = self._extract_prompt(input)
        response = self._call_gemini(prompt)
        return AIMessage(content=response)

    def with_structured_output(self, schema_class: Any) -> "GeminiStructuredOutput":
        return GeminiStructuredOutput(self, schema_class)
    
    @property
    def InputType(self) -> Any:
        return Any
    
    @property
    def OutputType(self) -> Any:
        return AIMessage


class GeminiStructuredOutput(RunnableSerializable):
    client: Any = None
    schema_class: Any = None
    
    def __init__(self, client: GeminiCLI, schema_class: Any, **kwargs):
        super().__init__(**kwargs)
        self.client = client
        self.schema_class = schema_class

    def _get_schema_prompt(self) -> str:
        schema = self.schema_class.model_json_schema()
        return f"Respond ONLY with valid JSON matching this schema (no markdown, no explanation, just JSON):\n{json.dumps(schema, indent=2)}"

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

    def invoke(self, input: Any, config: Optional[dict] = None, **kwargs) -> Any:
        prompt = self.client._extract_prompt(input)
        full_prompt = f"{self._get_schema_prompt()}\n\n{prompt}"
        
        if self.client.dev_mode:
            logger.debug(f"[Gemini CLI STRUCTURED REQUEST]: {full_prompt[:500]}")
        
        response = self.client._call_gemini(full_prompt)
        
        try:
            json_data = self._extract_json(response)
            result = self.schema_class(**json_data)
            
            if self.client.dev_mode:
                logger.debug(f"[Gemini CLI STRUCTURED RESPONSE]: {result}")
            
            return result
        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"Failed to parse Gemini response as JSON: {e}")
            logger.error(f"Raw response: {response[:500]}")
            raise RuntimeError(f"Failed to parse Gemini response: {e}")
    
    @property
    def InputType(self) -> Any:
        return Any
    
    @property
    def OutputType(self) -> Any:
        return self.schema_class
