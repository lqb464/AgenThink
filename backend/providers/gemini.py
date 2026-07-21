"""
Gemini LLM provider with function calling, multimodal, streaming,
and multi-key round-robin / failover on rate-limit & quota errors.
"""

from __future__ import annotations

import json
import logging
import threading
from collections.abc import AsyncGenerator, Callable
from typing import TypeVar

from openai import APIStatusError, AsyncOpenAI, OpenAI, RateLimitError

from backend.core.config import settings
from backend.providers.base import BaseLLMProvider, FunctionCall, LLMResponse

logger = logging.getLogger(__name__)

T = TypeVar("T")

_RATE_LIMIT_MARKERS = (
    "429",
    "rate limit",
    "rate_limit",
    "quota",
    "resource_exhausted",
    "resource exhausted",
    "too many requests",
    "exceeded your current quota",
)


def _is_rate_limit_error(exc: BaseException) -> bool:
    if isinstance(exc, RateLimitError):
        return True
    if isinstance(exc, APIStatusError) and getattr(exc, "status_code", None) == 429:
        return True
    status = getattr(exc, "status_code", None)
    if status == 429:
        return True
    msg = str(exc).lower()
    return any(marker in msg for marker in _RATE_LIMIT_MARKERS)


class _KeyPool:
    """Round-robin key pool with failover rotation on rate limits."""

    def __init__(self, keys: list[str]):
        if not keys:
            raise ValueError(
                "No Gemini API keys configured. Set GEMINI_API_KEY, "
                "GEMINI_API_KEYS, and/or GEMINI_API_KEY_1..N"
            )
        self._keys = keys
        self._index = 0
        self._lock = threading.Lock()
        logger.info("Gemini key pool ready (%d key(s))", len(keys))

    @property
    def size(self) -> int:
        return len(self._keys)

    def current(self) -> str:
        with self._lock:
            return self._keys[self._index % len(self._keys)]

    def advance(self) -> str:
        """Move to the next key (round-robin) and return it."""
        with self._lock:
            self._index = (self._index + 1) % len(self._keys)
            return self._keys[self._index]

    def mark_failed_and_rotate(self) -> str:
        """Rotate after a rate-limit/quota failure; returns the new key."""
        return self.advance()


class GeminiProvider(BaseLLMProvider):

    def __init__(self, model: str | None = None):
        keys = settings.get_gemini_api_keys()
        self._pool = _KeyPool(keys)
        self.model = model or settings.GEMINI_MODEL
        self._rebuild_clients(self._pool.current())

    def _rebuild_clients(self, api_key: str) -> None:
        self.client = OpenAI(
            api_key=api_key,
            base_url=settings.GEMINI_BASE_URL,
        )
        self.async_client = AsyncOpenAI(
            api_key=api_key,
            base_url=settings.GEMINI_BASE_URL,
        )

    def _rotate_clients(self) -> None:
        new_key = self._pool.mark_failed_and_rotate()
        self._rebuild_clients(new_key)
        logger.warning(
            "Gemini rate-limit/quota hit — rotated API key (pool size=%d)",
            self._pool.size,
        )

    def _round_robin_start(self) -> None:
        """Spread load across keys when more than one is configured."""
        if self._pool.size <= 1:
            return
        key = self._pool.advance()
        self._rebuild_clients(key)

    def _call_with_failover_sync(self, fn: Callable[[], T]) -> T:
        attempts = max(1, self._pool.size)
        last_exc: BaseException | None = None
        for attempt in range(attempts):
            try:
                return fn()
            except Exception as exc:
                last_exc = exc
                if _is_rate_limit_error(exc) and attempt < attempts - 1:
                    self._rotate_clients()
                    continue
                raise
        assert last_exc is not None
        raise last_exc

    async def _call_with_failover_async(self, fn: Callable):
        attempts = max(1, self._pool.size)
        last_exc: BaseException | None = None
        for attempt in range(attempts):
            try:
                return await fn()
            except Exception as exc:
                last_exc = exc
                if _is_rate_limit_error(exc) and attempt < attempts - 1:
                    self._rotate_clients()
                    continue
                raise
        assert last_exc is not None
        raise last_exc

    def chat(self, message: str) -> str:
        """Simple chat — backward compatible with existing code."""
        self._round_robin_start()

        def _do():
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": message}],
            )
            return response.choices[0].message.content

        return self._call_with_failover_sync(_do)

    async def chat_with_tools(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
    ) -> LLMResponse:
        """Send messages with tool definitions and return structured response."""
        self._round_robin_start()

        async def _do():
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

        return await self._call_with_failover_async(_do)

    async def chat_stream(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
    ) -> AsyncGenerator[dict, None]:
        """Stream chat response with support for function calls and key failover."""
        self._round_robin_start()
        attempts = max(1, self._pool.size)
        last_exc: BaseException | None = None

        for attempt in range(attempts):
            try:
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
                                tool_calls_acc[idx] = {
                                    "name": "",
                                    "arguments": "",
                                    "call_id": "",
                                }
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
                return

            except Exception as exc:
                last_exc = exc
                if _is_rate_limit_error(exc) and attempt < attempts - 1:
                    self._rotate_clients()
                    continue
                raise

        assert last_exc is not None
        raise last_exc
