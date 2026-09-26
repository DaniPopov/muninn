"""The OpenAI-compatible adapter against a fake HTTP server: the real SDK, no network.

Responses below have the shape of real Chat Completions responses.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import httpx
import pytest
from openai import AsyncOpenAI

from app.adapters.llm.openai_compatible import OpenAICompatibleLanguageModel
from app.domain.agent.exceptions import LanguageModelError, LanguageModelUnavailableError
from app.domain.agent.models import Message, TokenUsage, ToolCall, ToolDefinition

Handler = Callable[[httpx.Request], httpx.Response]

DUE = "2026-10-02T10:00:00+03:00"
REMINDER_ARGS = f'{{"text": "Ask Guy", "due_at": "{DUE}"}}'

SAVE_MEMORY = ToolDefinition(
    name="save_memory",
    description="Save something the user wants remembered.",
    parameters={
        "type": "object",
        "properties": {"text": {"type": "string"}},
        "required": ["text"],
    },
)


def completion(message: dict[str, Any], usage: dict[str, int] | None = None) -> dict[str, Any]:
    return {
        "id": "chatcmpl-123",
        "object": "chat.completion",
        "created": 1790000000,
        "model": "test-model",
        "choices": [{"index": 0, "message": message, "finish_reason": "stop"}],
        "usage": usage or {"prompt_tokens": 120, "completion_tokens": 8, "total_tokens": 128},
    }


def text_message(content: str) -> dict[str, Any]:
    return {"role": "assistant", "content": content}


def tool_call_message(*calls: tuple[str, str, str]) -> dict[str, Any]:
    return {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {"id": call_id, "type": "function", "function": {"name": name, "arguments": args}}
            for call_id, name, args in calls
        ],
    }


class FakeServer:
    """Answers every request with `respond(request)` and remembers the request bodies."""

    def __init__(self, respond: Handler) -> None:
        self._respond = respond
        self.requests: list[dict[str, Any]] = []

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(json.loads(request.content))
        return self._respond(request)


def model_for(server: FakeServer) -> OpenAICompatibleLanguageModel:
    client = AsyncOpenAI(
        base_url="https://llm.test/v1",
        api_key="sk-test",
        max_retries=0,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(server.handle)),
    )
    return OpenAICompatibleLanguageModel(client, "test-model")


def reply_with(body: dict[str, Any], status: int = 200) -> FakeServer:
    return FakeServer(lambda _request: httpx.Response(status, json=body))


# ---- request mapping ------------------------------------------------------------


async def test_sends_model_messages_and_tools_in_api_format() -> None:
    server = reply_with(completion(text_message("ok")))
    history = [
        Message.system("You are Muninn."),
        Message.user("I parked on floor 3"),
        Message.assistant(tool_calls=(ToolCall("call_1", "save_memory", {"text": "floor 3"}),)),
        Message.tool_result("call_1", "Saved"),
        Message.assistant("Got it."),
        Message.user("where did I park?"),
    ]

    await model_for(server).complete(history, [SAVE_MEMORY])

    body = server.requests[0]
    assert body["model"] == "test-model"
    assert body["messages"] == [
        {"role": "system", "content": "You are Muninn."},
        {"role": "user", "content": "I parked on floor 3"},
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {"name": "save_memory", "arguments": '{"text": "floor 3"}'},
                }
            ],
        },
        {"role": "tool", "tool_call_id": "call_1", "content": "Saved"},
        {"role": "assistant", "content": "Got it."},
        {"role": "user", "content": "where did I park?"},
    ]
    assert body["tools"] == [
        {
            "type": "function",
            "function": {
                "name": "save_memory",
                "description": "Save something the user wants remembered.",
                "parameters": SAVE_MEMORY.parameters,
            },
        }
    ]


async def test_no_tools_means_no_tools_field() -> None:
    server = reply_with(completion(text_message("ok")))

    await model_for(server).complete([Message.user("hi")], [])

    assert "tools" not in server.requests[0]


async def test_hebrew_arguments_are_sent_readable() -> None:
    server = reply_with(completion(text_message("ok")))
    call = ToolCall("call_1", "save_memory", {"text": "החניתי בקומה 3"})

    await model_for(server).complete(
        [
            Message.user("x"),
            Message.assistant(tool_calls=(call,)),
            Message.tool_result("call_1", "ok"),
        ],
        [],
    )

    sent = server.requests[0]["messages"][1]["tool_calls"][0]["function"]["arguments"]
    assert sent == '{"text": "החניתי בקומה 3"}'


# ---- response mapping -----------------------------------------------------------


async def test_parses_a_text_answer_and_usage() -> None:
    usage = {"prompt_tokens": 812, "completion_tokens": 41, "total_tokens": 853}
    server = reply_with(completion(text_message("On floor 3."), usage))

    response = await model_for(server).complete([Message.user("where did I park?")], [])

    assert response.text == "On floor 3."
    assert response.tool_calls == ()
    assert response.usage == TokenUsage(812, 41)


async def test_parses_tool_calls() -> None:
    server = reply_with(
        completion(
            tool_call_message(
                ("call_a", "save_memory", '{"text": "Lent Guy 200 shekels"}'),
                (
                    "call_b",
                    "create_reminder",
                    '{"text": "Ask Guy", "due_at": "2026-10-02T10:00:00+03:00"}',
                ),
            )
        )
    )

    response = await model_for(server).complete([Message.user("x")], [SAVE_MEMORY])

    assert response.text == ""
    assert response.tool_calls == (
        ToolCall("call_a", "save_memory", {"text": "Lent Guy 200 shekels"}),
        ToolCall(
            "call_b", "create_reminder", {"text": "Ask Guy", "due_at": "2026-10-02T10:00:00+03:00"}
        ),
    )


@pytest.mark.parametrize("broken", ['{"text": "floor', "[1, 2]", "not json"])
async def test_broken_tool_arguments_are_kept_not_crashed_on(broken: str) -> None:
    server = reply_with(completion(tool_call_message(("call_1", "save_memory", broken))))

    response = await model_for(server).complete([Message.user("x")], [SAVE_MEMORY])

    call = response.tool_calls[0]
    assert call.arguments == {}
    assert call.invalid_arguments == broken


async def test_empty_arguments_mean_no_arguments() -> None:
    server = reply_with(completion(tool_call_message(("call_1", "list_reminders", ""))))

    response = await model_for(server).complete([Message.user("x")], [])

    assert response.tool_calls[0].arguments == {}
    assert response.tool_calls[0].invalid_arguments is None


async def test_missing_usage_counts_as_zero() -> None:
    body = completion(text_message("ok"))
    del body["usage"]

    response = await model_for(reply_with(body)).complete([Message.user("x")], [])

    assert response.usage == TokenUsage(0, 0)


async def test_no_choices_is_an_error() -> None:
    body = completion(text_message("ok"))
    body["choices"] = []

    with pytest.raises(LanguageModelError):
        await model_for(reply_with(body)).complete([Message.user("x")], [])


# ---- error mapping --------------------------------------------------------------


def error_body(message: str) -> dict[str, Any]:
    return {"error": {"message": message, "type": "error", "code": None}}


@pytest.mark.parametrize("status", [429, 500, 502, 503])
async def test_rate_limits_and_server_errors_are_unavailable(status: int) -> None:
    with pytest.raises(LanguageModelUnavailableError):
        await model_for(reply_with(error_body("busy"), status)).complete([Message.user("x")], [])


@pytest.mark.parametrize("status", [400, 404, 422])
async def test_bad_requests_are_errors_not_unavailable(status: int) -> None:
    with pytest.raises(LanguageModelError) as error:
        await model_for(reply_with(error_body("bad"), status)).complete([Message.user("x")], [])
    assert not isinstance(error.value, LanguageModelUnavailableError)


async def test_bad_credentials_point_at_the_setting_without_leaking_the_key() -> None:
    with pytest.raises(LanguageModelError) as error:
        await model_for(reply_with(error_body("Incorrect API key"), 401)).complete(
            [Message.user("x")], []
        )
    assert "LLM_API_KEY" in error.value.message
    assert "sk-test" not in error.value.message


async def test_timeout_is_unavailable() -> None:
    def time_out(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    with pytest.raises(LanguageModelUnavailableError):
        await model_for(FakeServer(time_out)).complete([Message.user("x")], [])


async def test_connection_failure_is_unavailable() -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    with pytest.raises(LanguageModelUnavailableError):
        await model_for(FakeServer(refuse)).complete([Message.user("x")], [])


# ---- construction -----------------------------------------------------------------


def test_model_name_is_required() -> None:
    client = AsyncOpenAI(base_url="https://llm.test/v1", api_key="x")
    with pytest.raises(ValueError, match="LLM_MODEL"):
        OpenAICompatibleLanguageModel(client, "  ")


def test_create_works_without_a_key_for_local_servers() -> None:
    model = OpenAICompatibleLanguageModel.create(
        base_url="http://localhost:11434/v1", model="local-model", api_key=None
    )
    assert model.model_name == "local-model"
