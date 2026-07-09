from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    LLM_PROVIDER: str

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