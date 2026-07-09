from openai import OpenAI

from app.core.config import settings
from app.providers.base import BaseLLMProvider


class GeminiProvider(BaseLLMProvider):

    def __init__(self):
        self.client = OpenAI(
            api_key=settings.GEMINI_API_KEY,
            base_url=settings.GEMINI_BASE_URL,
        )

    def chat(self, message: str) -> str:

        response = self.client.chat.completions.create(
            model=settings.GEMINI_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": message,
                }
            ],
        )

        return response.choices[0].message.content