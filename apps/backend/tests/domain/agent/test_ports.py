from __future__ import annotations

from collections.abc import Sequence

import pytest

from app.domain.agent.models import Message, ModelResponse, ToolDefinition
from app.domain.agent.ports import LanguageModel


def test_port_cannot_be_used_without_implementing_it() -> None:
    with pytest.raises(TypeError):
        LanguageModel()  # type: ignore[abstract]


async def test_a_minimal_adapter_satisfies_the_port() -> None:
    class EchoModel(LanguageModel):
        @property
        def model_name(self) -> str:
            return "echo"

        async def complete(
            self, messages: Sequence[Message], tools: Sequence[ToolDefinition]
        ) -> ModelResponse:
            return ModelResponse(text=messages[-1].content)

    response = await EchoModel().complete([Message.user("hi")], [])
    assert response.text == "hi"
