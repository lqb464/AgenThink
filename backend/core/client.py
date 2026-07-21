from backend.core.config import settings
from backend.core.request_context import get_context
from backend.providers.gemini import GeminiProvider
from backend.providers.openai import OpenAIProvider
from backend.providers.base import BaseLLMProvider


def get_llm(
    provider: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
) -> BaseLLMProvider:
    """
    Resolve LLM provider for this request.

    Profiles:
      - gemini → GeminiProvider
      - openai → cloud OpenAI-compat (OPENAI_* settings)
      - local  → OpenAI-compat against Ollama/vLLM base URL
    """
    ctx = get_context()
    name = (provider or ctx.llm_provider or settings.LLM_PROVIDER or "gemini").strip().lower()
    override_model = model or ctx.llm_model
    override_base = base_url or ctx.openai_base_url

    if name == "gemini":
        return GeminiProvider(model=override_model) if override_model else GeminiProvider()

    if name in ("openai", "local"):
        if name == "local":
            burl = override_base or settings.LOCAL_OPENAI_BASE_URL
            mdl = override_model or settings.LOCAL_OPENAI_MODEL
            key = settings.LOCAL_OPENAI_API_KEY or settings.OPENAI_API_KEY or "ollama"
        else:
            burl = override_base or settings.OPENAI_BASE_URL
            mdl = override_model or settings.OPENAI_MODEL
            key = settings.OPENAI_API_KEY or "sk-local"
        return OpenAIProvider(api_key=key, base_url=burl, model=mdl)

    raise ValueError(f"Unsupported provider: {name}")


class _LazyLLM:
    """Defer provider construction until first use (avoids import-time key errors)."""

    _inst: BaseLLMProvider | None = None

    def __getattr__(self, item):
        if self._inst is None:
            self._inst = get_llm()
        return getattr(self._inst, item)


llm = _LazyLLM()
