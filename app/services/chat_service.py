from app.core.client import llm


def chat(message: str) -> str:
    return llm.chat(message)