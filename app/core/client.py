from app.core.config import settings

from app.providers.gemini import GeminiProvider
from app.providers.openai import OpenAIProvider
from app.providers.base import BaseLLMProvider


def get_llm() -> BaseLLMProvider:

    if settings.LLM_PROVIDER == "gemini":
        return GeminiProvider()

    if settings.LLM_PROVIDER == "openai":
        return OpenAIProvider()

    raise ValueError("Unsupported provider")


llm = get_llm()