from __future__ import annotations

import pytest

from app.domain.agent.exceptions import InvalidMessageError, InvalidToolDefinitionError
from app.domain.agent.models import (
    Message,
    ModelResponse,
    Role,
    TokenUsage,
    ToolCall,
    ToolDefinition,
)

CALL = ToolCall(id="call_1", name="save_memory", arguments={"text": "floor 3"})


# ---- Message ------------------------------------------------------------------


def test_constructors_set_the_role() -> None:
    assert Message.system("You are Muninn").role is Role.SYSTEM
    assert Message.user("where did I park?").role is Role.USER
    assert Message.assistant("On floor 3.").role is Role.ASSISTANT
    assert Message.tool_result("call_1", "Saved").role is Role.TOOL


def test_assistant_message_can_carry_only_tool_calls() -> None:
    message = Message.assistant(tool_calls=(CALL,))
    assert message.content == ""
    assert message.tool_calls == (CALL,)


def test_tool_result_keeps_the_call_id() -> None:
    assert Message.tool_result("call_1", "Saved").tool_call_id == "call_1"


def test_only_assistant_messages_have_tool_calls() -> None:
    with pytest.raises(InvalidMessageError):
        Message(Role.USER, "hi", tool_calls=(CALL,))


def test_tool_message_needs_a_call_id() -> None:
    with pytest.raises(InvalidMessageError):
        Message(Role.TOOL, "Saved")


def test_only_tool_messages_have_a_call_id() -> None:
    with pytest.raises(InvalidMessageError):
        Message(Role.USER, "hi", tool_call_id="call_1")


@pytest.mark.parametrize("role", [Role.SYSTEM, Role.USER, Role.TOOL])
def test_non_assistant_messages_cannot_be_empty(role: Role) -> None:
    with pytest.raises(InvalidMessageError):
        Message(role, "", tool_call_id="call_1" if role is Role.TOOL else None)


def test_assistant_message_needs_text_or_tool_calls() -> None:
    with pytest.raises(InvalidMessageError):
        Message.assistant()


def test_messages_are_immutable() -> None:
    message = Message.user("hi")
    with pytest.raises(AttributeError):
        message.content = "changed"  # type: ignore[misc]


# ---- ToolDefinition -----------------------------------------------------------


def test_valid_tool_definition() -> None:
    tool = ToolDefinition("save_memory", "Save something.", {"type": "object"})
    assert tool.name == "save_memory"


@pytest.mark.parametrize("name", ["", "save memory", "שמור", "a" * 65, "save.memory"])
def test_tool_name_format_is_enforced(name: str) -> None:
    with pytest.raises(InvalidToolDefinitionError):
        ToolDefinition(name, "Save something.", {"type": "object"})


def test_tool_needs_a_description() -> None:
    with pytest.raises(InvalidToolDefinitionError):
        ToolDefinition("save_memory", "  ", {"type": "object"})


# ---- TokenUsage ---------------------------------------------------------------


def test_token_usage_adds_up() -> None:
    total = TokenUsage(800, 40) + TokenUsage(700, 37)
    assert total == TokenUsage(1500, 77)
    assert total.total_tokens == 1577


def test_token_usage_cannot_be_negative() -> None:
    with pytest.raises(ValueError, match="negative"):
        TokenUsage(-1, 0)


# ---- ModelResponse ------------------------------------------------------------


def test_text_response_does_not_want_tools() -> None:
    response = ModelResponse(text="On floor 3.")
    assert not response.wants_tools
    assert response.as_message() == Message.assistant("On floor 3.")


def test_tool_call_response_becomes_an_assistant_message_with_calls() -> None:
    response = ModelResponse(tool_calls=(CALL,), usage=TokenUsage(10, 5))
    assert response.wants_tools
    assert response.as_message().tool_calls == (CALL,)
