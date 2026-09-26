"""A scripted LanguageModel for tests: returns the responses you give it, in order.

It also records every call, so a test can check exactly what the harness sent.
"""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass

from app.domain.agent.exceptions import LanguageModelError
from app.domain.agent.models import Message, ModelResponse, ToolDefinition
from app.domain.agent.ports import LanguageModel


@dataclass(frozen=True)
class RecordedCall:
    messages: tuple[Message, ...]
    tools: tuple[ToolDefinition, ...]


class FakeLanguageModel(LanguageModel):
    def __init__(
        self,
        script: Sequence[ModelResponse | Exception],
        *,
        delay_seconds: float = 0.0,
    ) -> None:
        self._script = list(script)
        self._delay = delay_seconds
        self.calls: list[RecordedCall] = []

    @property
    def model_name(self) -> str:
        return "fake"

    async def complete(
        self, messages: Sequence[Message], tools: Sequence[ToolDefinition]
    ) -> ModelResponse:
        self.calls.append(RecordedCall(tuple(messages), tuple(tools)))
        if self._delay:
            await asyncio.sleep(self._delay)
        if not self._script:
            raise LanguageModelError("The fake model has no more scripted responses.")
        step = self._script.pop(0)
        if isinstance(step, Exception):
            raise step
        return step
