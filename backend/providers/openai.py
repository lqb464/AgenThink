"""
OpenAI LLM provider with function calling, multimodal, and streaming support.
"""

import json
import logging
from collections.abc import AsyncGenerator

from openai import AsyncOpenAI, OpenAI

from backend.core.config import settings
from backend.providers.base import BaseLLMProvider, FunctionCall, LLMResponse

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseLLMProvider):

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ):
        self.model = model or settings.OPENAI_MODEL
        key = api_key or settings.OPENAI_API_KEY
        url = base_url or settings.OPENAI_BASE_URL
        self.client = OpenAI(api_key=key, base_url=url)
        self.async_client = AsyncOpenAI(api_key=key, base_url=url)

    def chat(self, message: str) -> str:
        """Simple chat — backward compatible."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": message}],
        )
        return response.choices[0].message.content

    async def chat_with_tools(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
    ) -> LLMResponse:
        kwargs = {
            "model": self.model,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        response = await self.async_client.chat.completions.create(**kwargs)
        choice = response.choices[0]
        message = choice.message

        function_calls = []
        if message.tool_calls:
            for tc in message.tool_calls:
                try:
                    args = (
                        json.loads(tc.function.arguments)
                        if isinstance(tc.function.arguments, str)
                        else tc.function.arguments
                    )
                except (json.JSONDecodeError, TypeError):
                    args = {}
                function_calls.append(
                    FunctionCall(
                        name=tc.function.name,
                        arguments=args,
                        call_id=tc.id or "",
                    )
                )

        return LLMResponse(
            text=message.content or "",
            function_calls=function_calls,
            finish_reason=choice.finish_reason or "",
        )

    async def chat_stream(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
    ) -> AsyncGenerator[dict, None]:
        kwargs = {
            "model": self.model,
            "messages": messages,
            "stream": True,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        stream = await self.async_client.chat.completions.create(**kwargs)

        tool_calls_acc: dict[int, dict] = {}
        finish_reason = None

        async for chunk in stream:
            if not chunk.choices:
                continue

            delta = chunk.choices[0].delta
            finish_reason = chunk.choices[0].finish_reason

            if delta.content:
                yield {"type": "text", "content": delta.content}

            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    if idx not in tool_calls_acc:
                        tool_calls_acc[idx] = {"name": "", "arguments": "", "call_id": ""}
                    if tc.function and tc.function.name:
                        tool_calls_acc[idx]["name"] = tc.function.name
                    if tc.function and tc.function.arguments:
                        tool_calls_acc[idx]["arguments"] += tc.function.arguments
                    if tc.id:
                        tool_calls_acc[idx]["call_id"] = tc.id

        for _idx, tc_data in sorted(tool_calls_acc.items()):
            try:
                args = json.loads(tc_data["arguments"]) if tc_data["arguments"] else {}
            except json.JSONDecodeError:
                args = {}
            yield {
                "type": "function_call",
                "name": tc_data["name"],
                "arguments": args,
                "call_id": tc_data["call_id"],
            }

        yield {"type": "done", "finish_reason": finish_reason or "stop"}
