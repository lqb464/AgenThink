from openai import OpenAI

from app.core.config import settings
from app.providers.base import BaseLLMProvider


class OpenAIProvider(BaseLLMProvider):

    def __init__(self):
        self.client = OpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
        )

    def chat(self, message: str) -> str:

        response = self.client.responses.create(
            model=settings.OPENAI_MODEL,
            input=message,
        )

        return response.output_text