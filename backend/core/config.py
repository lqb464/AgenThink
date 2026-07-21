from pydantic_settings import BaseSettings, SettingsConfigDict


def _split_keys(raw: str) -> list[str]:
    """Split comma/semicolon/newline-separated API keys; drop empties."""
    if not raw or not raw.strip():
        return []
    parts: list[str] = []
    for chunk in raw.replace(";", ",").replace("\n", ",").split(","):
        key = chunk.strip().strip('"').strip("'")
        if key:
            parts.append(key)
    return parts


class Settings(BaseSettings):
    LLM_PROVIDER: str = "gemini"
    SYSTEM_PROMPT: str = "You are a helpful assistant. Answer briefly and clearly with 'Dạ' or 'Vâng'. Always respond in Vietnamese, regardless of the language used in the question."

    # Primary key (also accepted as first entry). Multi-key: GEMINI_API_KEYS or GEMINI_API_KEY_1..N
    GEMINI_API_KEY: str = ""
    GEMINI_API_KEYS: str = ""
    GEMINI_API_KEY_1: str = ""
    GEMINI_API_KEY_2: str = ""
    GEMINI_API_KEY_3: str = ""
    GEMINI_API_KEY_4: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta/openai/"

    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-5"
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"

    # Production knobs
    API_TOKEN: str = ""  # legacy shared bearer (optional)
    RATE_LIMIT_MAX_CALLS: int = 30
    RATE_LIMIT_WINDOW_SECONDS: float = 60.0
    CACHE_ENABLED: bool = True
    ESTIMATED_COST_PER_CALL_USD: float = 0.0002

    # JWT multi-user
    JWT_SECRET: str = "change-me-dev-only-not-for-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_MINUTES: int = 60
    JWT_REFRESH_DAYS: int = 14
    # When true, chat/docs/sessions require a valid JWT (or legacy API_TOKEN)
    AUTH_REQUIRED: bool = True
    SEED_DEMO_USER: bool = False
    DEMO_USER_EMAIL: str = "demo@local"
    DEMO_USER_PASSWORD: str = "change-me"

    # Local OpenAI-compat presets (model picker → Local)
    LOCAL_OPENAI_BASE_URL: str = "http://127.0.0.1:11434/v1"  # Ollama default
    VLLM_OPENAI_BASE_URL: str = "http://127.0.0.1:8000/v1"
    LOCAL_OPENAI_MODEL: str = "llama3.2"
    LOCAL_OPENAI_API_KEY: str = "ollama"

    # Local RAG (in-process) — Tri thức storage
    RAG_DATA_DIR: str = "./data/rag"
    RAG_PROJECT_ID: str = "agentthink_default"
    RAG_EMBED_MODEL: str = "text-embedding-004"

    # Free research browsing — empty disables SearXNG soft-fail path
    SEARXNG_URL: str = ""
    SEARCH_RATE_LIMIT_MAX_CALLS: int = 20
    SEARCH_RATE_LIMIT_WINDOW_SECONDS: float = 60.0
    ENABLE_DDG_FALLBACK: bool = False

    # Database
    DATABASE_URL: str = "sqlite:///chat_memory.db"

    # Feature flags
    ENABLE_STREAMING: bool = True
    ENABLE_MULTIMODAL: bool = True

    # Agent loop budgets
    MAX_TOOL_ROUNDS: int = 10
    MAX_LLM_CALLS_PER_TURN: int = 14
    ENABLE_AGENT_PLANNING: bool = True
    ENABLE_AGENT_REFLECTION: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    @staticmethod
    def is_service_url_enabled(url: str | None) -> bool:
        """False when URL is blank or explicitly disabled."""
        raw = (url or "").strip().lower()
        if not raw:
            return False
        return raw not in {"off", "disabled", "none", "false", "0"}

    def get_gemini_api_keys(self) -> list[str]:
        """Collect unique Gemini API keys from all supported env patterns (values never logged)."""
        ordered: list[str] = []
        seen: set[str] = set()

        def _add(raw: str) -> None:
            for key in _split_keys(raw):
                if key not in seen:
                    seen.add(key)
                    ordered.append(key)

        _add(self.GEMINI_API_KEY)
        _add(self.GEMINI_API_KEYS)
        for attr in (
            "GEMINI_API_KEY_1",
            "GEMINI_API_KEY_2",
            "GEMINI_API_KEY_3",
            "GEMINI_API_KEY_4",
        ):
            _add(getattr(self, attr, "") or "")

        # Also pick up GEMINI_API_KEY_5+ if present via env (optional)
        import os

        idx = 5
        while True:
            extra = os.getenv(f"GEMINI_API_KEY_{idx}", "")
            if not extra.strip():
                break
            _add(extra)
            idx += 1
            if idx > 20:
                break

        return ordered


settings = Settings()
