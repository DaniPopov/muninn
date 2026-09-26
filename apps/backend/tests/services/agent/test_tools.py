from __future__ import annotations

import pytest

from app.domain.agent.models import ToolCall
from app.services.agent.exceptions import DuplicateToolError
from app.services.agent.tools import ToolRegistry
from tests.services.agent.toy_tools import CrashingTool, EchoTool, RejectingTool


def _call(name: str, **arguments: object) -> ToolCall:
    return ToolCall(id="call_1", name=name, arguments=arguments)


def test_definition_comes_from_the_args_model() -> None:
    definition = EchoTool().definition()

    assert definition.name == "echo"
    assert definition.description == "Return the text you were given."
    assert definition.parameters["required"] == ["text"]
    assert definition.parameters["properties"]["text"]["description"] == "Text to echo back"


def test_registry_rejects_two_tools_with_the_same_name() -> None:
    with pytest.raises(DuplicateToolError):
        ToolRegistry([EchoTool(), EchoTool()])


def test_registry_lists_definitions() -> None:
    registry = ToolRegistry([EchoTool(), RejectingTool()])
    assert [d.name for d in registry.definitions()] == ["echo", "reject"]


async def test_execute_runs_the_tool() -> None:
    echo = EchoTool()
    outcome = await ToolRegistry([echo]).execute(_call("echo", text="floor 3"))

    assert outcome.ok
    assert outcome.content == "echo: floor 3"
    assert echo.received == ["floor 3"]


async def test_unknown_tool_is_an_error_for_the_model() -> None:
    outcome = await ToolRegistry([EchoTool()]).execute(_call("delete_everything"))

    assert not outcome.ok
    assert outcome.content == "error: no tool named 'delete_everything'"


async def test_invalid_arguments_are_an_error_for_the_model() -> None:
    echo = EchoTool()
    outcome = await ToolRegistry([echo]).execute(_call("echo", wrong="x"))

    assert not outcome.ok
    assert outcome.content == "error: invalid arguments: text: Field required"
    assert echo.received == []  # the tool never ran


async def test_domain_error_message_reaches_the_model() -> None:
    outcome = await ToolRegistry([RejectingTool()]).execute(_call("reject"))

    assert not outcome.ok
    assert outcome.content == "error: That reminder is in the past."


async def test_unexpected_error_is_hidden_from_the_model() -> None:
    outcome = await ToolRegistry([CrashingTool()]).execute(_call("crash"))

    assert not outcome.ok
    assert outcome.content == "error: the tool failed"
    assert "hunter2" not in outcome.content


async def test_arguments_that_were_not_json_are_an_error_for_the_model() -> None:
    echo = EchoTool()
    broken = ToolCall(id="call_1", name="echo", arguments={}, invalid_arguments='{"text": "fl')

    outcome = await ToolRegistry([echo]).execute(broken)

    assert not outcome.ok
    assert outcome.content == "error: arguments were not a valid JSON object"
    assert echo.received == []
