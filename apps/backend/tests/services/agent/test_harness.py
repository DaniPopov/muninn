"""The harness, tested offline with a scripted model. See docs/architecture/agent.md#testing."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from zoneinfo import ZoneInfo

import pytest

from app.adapters.llm.fake import FakeLanguageModel
from app.domain.agent.exceptions import LanguageModelError, LanguageModelUnavailableError
from app.domain.agent.models import (
    Message,
    ModelResponse,
    Role,
    TokenUsage,
    ToolCall,
)
from app.services.agent.exceptions import AgentError, AgentUnavailableError
from app.services.agent.harness import (
    FALLBACK_REPLY,
    MAX_TOOL_RESULT_CHARS,
    AgentHarness,
    trim_history,
)
from app.services.agent.prompt import SystemPrompt
from app.services.agent.tools import Tool, ToolRegistry
from tests.fakes import FixedClock
from tests.services.agent.toy_tools import (
    CrashingTool,
    EchoTool,
    HugeOutputTool,
    RejectingTool,
)

JERUSALEM = ZoneInfo("Asia/Jerusalem")


def text(reply: str, usage: TokenUsage | None = None) -> ModelResponse:
    return ModelResponse(text=reply, usage=usage or TokenUsage())


def calls(*tool_calls: ToolCall, usage: TokenUsage | None = None) -> ModelResponse:
    return ModelResponse(tool_calls=tool_calls, usage=usage or TokenUsage())


def call(name: str, call_id: str = "call_1", **arguments: object) -> ToolCall:
    return ToolCall(id=call_id, name=name, arguments=arguments)


def make_harness(
    model: FakeLanguageModel,
    tools: Sequence[Tool] | None = None,  # type: ignore[type-arg]
    **options: object,
) -> AgentHarness:
    return AgentHarness(
        model,
        ToolRegistry(tools if tools is not None else [EchoTool()]),
        SystemPrompt("You are Muninn. Now: {now} ({timezone})"),
        FixedClock(),
        JERUSALEM,
        **options,  # type: ignore[arg-type]
    )


# ---- the basic loop -------------------------------------------------------------


async def test_text_answer_ends_the_turn_in_one_step() -> None:
    model = FakeLanguageModel([text("On floor 3.")])

    result = await make_harness(model).run_turn("where did I park?")

    assert result.reply == "On floor 3."
    assert result.steps == 1
    assert result.completed
    assert [m.role for m in result.new_messages] == [Role.USER, Role.ASSISTANT]


async def test_model_receives_system_prompt_history_and_user_message() -> None:
    model = FakeLanguageModel([text("ok")])
    history = [Message.user("hi"), Message.assistant("Hello!")]

    await make_harness(model).run_turn("where did I park?", history)

    sent = model.calls[0].messages
    assert sent[0].role is Role.SYSTEM
    assert "Friday, 2026-09-25 10:00 (Asia/Jerusalem)" in sent[0].content
    assert sent[1:] == (*history, Message.user("where did I park?"))


async def test_model_receives_the_tool_definitions() -> None:
    model = FakeLanguageModel([text("ok")])

    await make_harness(model).run_turn("hi")

    assert [t.name for t in model.calls[0].tools] == ["echo"]


async def test_tool_call_runs_and_result_reaches_the_model() -> None:
    echo = EchoTool()
    model = FakeLanguageModel([calls(call("echo", text="floor 3")), text("Saved.")])

    result = await make_harness(model, [echo]).run_turn("I parked on floor 3")

    assert echo.received == ["floor 3"]
    assert result.reply == "Saved."
    assert result.steps == 2
    second_call = model.calls[1].messages
    assert second_call[-2].tool_calls == (call("echo", text="floor 3"),)
    assert second_call[-1] == Message.tool_result("call_1", "echo: floor 3")


async def test_several_tool_calls_in_one_step_run_in_order() -> None:
    echo = EchoTool()
    model = FakeLanguageModel(
        [
            calls(call("echo", "a", text="first"), call("echo", "b", text="second")),
            text("done"),
        ]
    )

    result = await make_harness(model, [echo]).run_turn("two things")

    assert echo.received == ["first", "second"]
    tool_messages = [m for m in result.new_messages if m.role is Role.TOOL]
    assert [m.tool_call_id for m in tool_messages] == ["a", "b"]


async def test_new_messages_hold_the_whole_turn() -> None:
    model = FakeLanguageModel([calls(call("echo", text="x")), text("done")])

    result = await make_harness(model).run_turn("go")

    assert [m.role for m in result.new_messages] == [
        Role.USER,
        Role.ASSISTANT,  # with the tool call
        Role.TOOL,
        Role.ASSISTANT,  # the reply
    ]


async def test_usage_is_summed_over_all_steps() -> None:
    model = FakeLanguageModel(
        [
            calls(call("echo", text="x"), usage=TokenUsage(800, 40)),
            text("done", usage=TokenUsage(900, 37)),
        ]
    )

    result = await make_harness(model).run_turn("go")

    assert result.usage == TokenUsage(1700, 77)


# ---- tool errors go back to the model -------------------------------------------


@pytest.mark.parametrize(
    ("tool_call", "expected"),
    [
        (call("nope"), "error: no tool named 'nope'"),
        (call("echo", wrong="x"), "error: invalid arguments: text: Field required"),
        (call("reject"), "error: That reminder is in the past."),
        (call("crash"), "error: the tool failed"),
    ],
)
async def test_tool_problems_become_error_results_not_crashes(
    tool_call: ToolCall, expected: str
) -> None:
    model = FakeLanguageModel([calls(tool_call), text("Sorry, that didn't work.")])
    tools = [EchoTool(), RejectingTool(), CrashingTool()]

    result = await make_harness(model, tools).run_turn("do it")

    assert result.reply == "Sorry, that didn't work."
    assert model.calls[1].messages[-1].content == expected


async def test_long_tool_results_are_truncated() -> None:
    model = FakeLanguageModel([calls(call("huge")), text("ok")])

    await make_harness(model, [HugeOutputTool()]).run_turn("go")

    sent = model.calls[1].messages[-1].content
    assert sent.startswith("x" * MAX_TOOL_RESULT_CHARS)
    assert sent.endswith("[truncated: 6000 more characters]")


# ---- limits and failures --------------------------------------------------------


async def test_step_limit_stops_a_model_that_never_answers() -> None:
    model = FakeLanguageModel([calls(call("echo", text="again"))] * 10)

    result = await make_harness(model, max_steps=3).run_turn("loop forever")

    assert result.reply == FALLBACK_REPLY
    assert not result.completed
    assert result.steps == 3
    assert len(model.calls) == 3
    assert result.new_messages[-1] == Message.assistant(FALLBACK_REPLY)


async def test_empty_answer_falls_back() -> None:
    model = FakeLanguageModel([ModelResponse()])

    result = await make_harness(model).run_turn("hi")

    assert result.reply == FALLBACK_REPLY
    assert not result.completed


async def test_turn_timeout_raises_unavailable() -> None:
    model = FakeLanguageModel([text("too late")], delay_seconds=1.0)

    with pytest.raises(AgentUnavailableError):
        await make_harness(model, turn_timeout_seconds=0.05).run_turn("hi")


async def test_unavailable_model_raises_unavailable() -> None:
    model = FakeLanguageModel([LanguageModelUnavailableError("rate limited")])

    with pytest.raises(AgentUnavailableError) as error:
        await make_harness(model).run_turn("hi")
    assert error.value.code == "agent_unavailable"


async def test_other_model_errors_raise_agent_error() -> None:
    model = FakeLanguageModel([LanguageModelError("bad request")])

    with pytest.raises(AgentError) as error:
        await make_harness(model).run_turn("hi")
    assert error.value.code == "agent_failed"


# ---- history trimming -------------------------------------------------------------


def test_trim_keeps_the_most_recent_messages() -> None:
    history = [
        Message.user(f"q{i}") if i % 2 == 0 else Message.assistant(f"a{i}") for i in range(30)
    ]

    trimmed = trim_history(history, limit=4)

    assert [m.content for m in trimmed] == ["q26", "a27", "q28", "a29"]


def test_trim_never_starts_with_an_orphan_tool_result() -> None:
    history = [
        Message.user("save it"),
        Message.assistant(tool_calls=(call("echo", text="x"),)),
        Message.tool_result("call_1", "echo: x"),
        Message.assistant("Saved."),
        Message.user("thanks"),
        Message.assistant("You're welcome."),
    ]

    trimmed = trim_history(history, limit=4)  # a blind cut would start at the tool result

    assert trimmed[0] == Message.user("thanks")


# ---- privacy of logs ----------------------------------------------------------------


async def test_user_text_is_not_logged_by_default(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    model = FakeLanguageModel([calls(call("echo", text="secret 1234")), text("done")])

    await make_harness(model).run_turn("my PIN is secret 1234")

    assert "secret 1234" not in caplog.text
    assert "agent.step" in caplog.text
    assert "agent.turn" in caplog.text


async def test_user_text_is_logged_when_enabled_for_dev(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    model = FakeLanguageModel([text("done")])

    await make_harness(model, log_content=True).run_turn("hello there")

    assert "hello there" in caplog.text
