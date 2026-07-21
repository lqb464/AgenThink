from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    language: str | None = "vi"
    llm_provider: str | None = None
    llm_model: str | None = None
    openai_base_url: str | None = None


class ChatResponse(BaseModel):
    response: str
    session_id: str | None = None
    request_id: str | None = None
    cached: bool = False
    estimated_cost_usd: float | None = None
