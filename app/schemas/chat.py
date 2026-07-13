from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str
    request_id: str | None = None
    cached: bool = False
    estimated_cost_usd: float | None = None
