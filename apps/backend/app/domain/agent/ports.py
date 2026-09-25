"""What the agent needs from the outside world: a language model.

One adapter per provider API implements this (adapters/llm/). The harness only ever
talks to this interface. See docs/architecture/agent.md#the-port.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from app.domain.agent.models import Message, ModelResponse, ToolDefinition


class LanguageModel(ABC):
    @property
    @abstractmethod
    def model_name(self) -> str:
        """The model's name as the provider calls it. Used in logs."""

    @abstractmethod
    async def complete(
        self, messages: Sequence[Message], tools: Sequence[ToolDefinition]
    ) -> ModelResponse:
        """One model call.

        Raises LanguageModelUnavailableError on timeouts, rate limits, 5xx and network
        errors (worth trying again later), and LanguageModelError on anything else.
        """
