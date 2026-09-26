from __future__ import annotations

import pytest

from app.adapters.llm.fake import FakeLanguageModel
from app.domain.agent.exceptions import LanguageModelError
from app.domain.agent.models import Message, ModelResponse


async def test_returns_script_in_order_and_records_calls() -> None:
    model = FakeLanguageModel([ModelResponse(text="one"), ModelResponse(text="two")])

    first = await model.complete([Message.user("a")], [])
    second = await model.complete([Message.user("b")], [])

    assert (first.text, second.text) == ("one", "two")
    assert [c.messages[-1].content for c in model.calls] == ["a", "b"]


async def test_raises_when_the_script_runs_out() -> None:
    with pytest.raises(LanguageModelError):
        await FakeLanguageModel([]).complete([Message.user("a")], [])
