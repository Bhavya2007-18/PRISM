"""
PRISM LLM Service — LiteLLM-powered provider abstraction.
Resilient LLM calls with automatic fallback.
If primary provider fails, transparently switches to fallback.
"""
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def get_llm_config() -> dict:
    return {
        "model": os.getenv("LLM_MODEL", "openai/gpt-oss-20b"),
        "api_key": os.getenv("LLM_API_KEY", ""),
        "api_base": os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1"),
        "fallback_model": os.getenv("LITELLM_FALLBACK_MODEL", ""),
        "fallback_api_key": os.getenv("LITELLM_FALLBACK_API_KEY", ""),
        "fallback_api_base": os.getenv("LITELLM_FALLBACK_API_BASE", ""),
    }


async def prism_llm_call(
    messages: list,
    tools: Optional[list] = None,
    tool_choice: str = "auto",
    max_tokens: int = 250,
    temperature: float = 0.7,
) -> dict:
    """
    Resilient LLM call via LiteLLM.
    Tries primary model first, falls back to secondary if configured and primary fails.
    Returns dict compatible with OpenAI response format.
    """
    try:
        import litellm
        litellm.set_verbose = False
        litellm.suppress_debug_info = True
        from litellm import acompletion
    except ImportError:
        raise RuntimeError("litellm not installed — run: pip install litellm")

    cfg = get_llm_config()

    kwargs = {
        "model": cfg["model"],
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": False,
        "api_key": cfg["api_key"],
        "api_base": cfg["api_base"],
    }
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = tool_choice

    # Try primary
    try:
        response = await acompletion(**kwargs)
        return response.model_dump()
    except Exception as primary_err:
        logger.warning(f"[PRISM LLM] Primary provider failed: {primary_err}")
        # Try fallback if configured
        if cfg["fallback_model"]:
            fallback_kwargs = {**kwargs}
            fallback_kwargs["model"] = cfg["fallback_model"]
            if cfg["fallback_api_key"]:
                fallback_kwargs["api_key"] = cfg["fallback_api_key"]
            if cfg["fallback_api_base"]:
                fallback_kwargs["api_base"] = cfg["fallback_api_base"]
            try:
                response = await acompletion(**fallback_kwargs)
                logger.info("[PRISM LLM] Fallback provider succeeded")
                return response.model_dump()
            except Exception as fallback_err:
                raise RuntimeError(f"Both LLM providers failed. Primary: {primary_err}. Fallback: {fallback_err}")
        raise RuntimeError(f"LLM call failed: {primary_err}")
