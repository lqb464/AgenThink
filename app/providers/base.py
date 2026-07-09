from abc import ABC, abstractmethod


class BaseLLMProvider(ABC):

    @abstractmethod
    def chat(self, message: str) -> str:
        """Send a message to the LLM and return the response."""
        raise NotImplementedError