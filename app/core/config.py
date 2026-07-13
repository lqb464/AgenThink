from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    LLM_PROVIDER: str
    SYSTEM_PROMPT: str = "You are a helpful assistant. Answer briefly and clearly with 'Dạ' or 'Vâng'. Always respond in Vietnamese, regardless of the language used in the question."

    GEMINI_API_KEY: str
    GEMINI_MODEL: str
    GEMINI_BASE_URL: str

    OPENAI_API_KEY: str
    OPENAI_MODEL: str
    OPENAI_BASE_URL: str

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()