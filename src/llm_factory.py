import os
import logging
from typing import Any

logger = logging.getLogger("atmio.llm")


def get_llm():
    provider = os.getenv("LLM_PROVIDER", "openrouter").lower()
    
    if provider == "gemini":
        from src.gemini_client import GeminiCLI
        logger.info("Using Gemini CLI as LLM provider")
        return GeminiCLI()
    else:
        from src.openrouter_client import RateLimitedOpenRouterLLM
        logger.info(f"Using OpenRouter as LLM provider (model: {os.getenv('OPENROUTER_MODEL', 'default')})")
        return RateLimitedOpenRouterLLM()
