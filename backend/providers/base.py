from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from typing import Any


@dataclass
class FunctionCall:
    """Represents a function call requested by the LLM."""

    name: str
    arguments: dict
    call_id: str = ""


@dataclass
class LLMResponse:
    """Structured response from the LLM."""

    text: str = ""
    function_calls: list[FunctionCall] = field(default_factory=list)
    finish_reason: str = ""

    @property
    def has_function_calls(self) -> bool:
        return len(self.function_calls) > 0


class BaseLLMProvider(ABC):

    @abstractmethod
    def chat(self, message: str) -> str:
        """Send a message to the LLM and return the response."""
        raise NotImplementedError

    @abstractmethod
    async def chat_with_tools(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
    ) -> LLMResponse:
        """Send messages with tool definitions and return structured response."""
        raise NotImplementedError

    @abstractmethod
    async def chat_stream(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
    ) -> AsyncGenerator[dict, None]:
        """
        Stream chat response chunks.

        Yields dicts with keys:
        - {"type": "text", "content": "..."} for text chunks
        - {"type": "function_call", "name": "...", "arguments": {...}, "call_id": "..."} for tool calls
        - {"type": "done", "finish_reason": "..."} when complete
        """
        raise NotImplementedError
        # Make this an async generator
        yield  # pragma: no cover