"""LanguageModel adapter for OpenAI, and any server that speaks the same API.

It uses the Chat Completions API (not OpenAI's newer Responses API) because that is the
format Ollama, vLLM, OpenRouter and most other servers copy, so this one adapter covers
all of them with a different base URL (ADR 0007, docs/architecture/agent.md).

This is the only file that knows the OpenAI SDK. It maps our domain types to the API's
format and back, and turns SDK errors into our LanguageModel errors.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

import openai
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion

from app.domain.agent.exceptions import LanguageModelError, LanguageModelUnavailableError
from app.domain.agent.models import (
    Message,
    ModelResponse,
    Role,
    TokenUsage,
    ToolCall,
    ToolDefinition,
)
from app.domain.agent.ports import LanguageModel

MODEL_CALL_TIMEOUT_SECONDS = 20.0

# Local servers (Ollama, vLLM) don't check the key, but the SDK refuses to start without one.
_NO_KEY = "not-needed"


class OpenAICompatibleLanguageModel(LanguageModel):
    def __init__(
        self, client: AsyncOpenAI, model: str, *, reasoning_effort: str | None = None
    ) -> None:
        if not model.strip():
            raise ValueError("LLM_MODEL is not set. Put the model name in .env.")
        self._client = client
        self._model = model
        self._reasoning_effort = reasoning_effort

    @classmethod
    def create(
        cls,
        *,
        base_url: str,
        model: str,
        api_key: str | None,
        reasoning_effort: str | None = None,
        timeout_seconds: float = MODEL_CALL_TIMEOUT_SECONDS,
    ) -> OpenAICompatibleLanguageModel:
        client = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key or _NO_KEY,
            timeout=timeout_seconds,
            # No automatic retries in v1: the harness has a turn timeout, and a user
            # waiting on WhatsApp is better served by a quick "try again" than a long wait.
            max_retries=0,
        )
        return cls(client, model, reasoning_effort=reasoning_effort)

    @property
    def model_name(self) -> str:
        return self._model

    async def complete(
        self, messages: Sequence[Message], tools: Sequence[ToolDefinition]
    ) -> ModelResponse:
        request: dict[str, Any] = {
            "model": self._model,
            "messages": [_to_api_message(m) for m in messages],
        }
        if tools:  # the API rejects an empty tool list
            request["tools"] = [_to_api_tool(t) for t in tools]
        if self._reasoning_effort:  # many compatible servers don't know this field
            request["reasoning_effort"] = self._reasoning_effort

        try:
            completion = await self._client.chat.completions.create(**request)
        except (openai.APITimeoutError, openai.APIConnectionError) as exc:
            raise LanguageModelUnavailableError(
                f"Can't reach the model: {type(exc).__name__}"
            ) from exc
        except openai.RateLimitError as exc:
            raise LanguageModelUnavailableError("The model provider is rate limiting us.") from exc
        except openai.APIStatusError as exc:
            if exc.status_code >= 500:
                raise LanguageModelUnavailableError(
                    f"The model provider returned {exc.status_code}."
                ) from exc
            if exc.status_code in (401, 403):
                raise LanguageModelError(
                    "The model provider rejected our credentials. Check LLM_API_KEY."
                ) from exc
            raise LanguageModelError(
                f"The model provider rejected the request ({exc.status_code})."
            ) from exc
        except openai.APIError as exc:
            raise LanguageModelError(f"Model call failed: {type(exc).__name__}") from exc

        return _from_api_completion(completion)


# ---- our types -> API ---------------------------------------------------------


def _to_api_message(message: Message) -> dict[str, Any]:
    if message.role is Role.TOOL:
        return {"role": "tool", "tool_call_id": message.tool_call_id, "content": message.content}

    if message.role is Role.ASSISTANT and message.tool_calls:
        return {
            "role": "assistant",
            "content": message.content or None,
            "tool_calls": [_to_api_tool_call(call) for call in message.tool_calls],
        }

    return {"role": message.role.value, "content": message.content}


def _to_api_tool_call(call: ToolCall) -> dict[str, Any]:
    # Send broken arguments back exactly as the model wrote them, so the history is honest.
    arguments = (
        call.invalid_arguments
        if call.invalid_arguments is not None
        else json.dumps(dict(call.arguments), ensure_ascii=False)
    )
    return {
        "id": call.id,
        "type": "function",
        "function": {"name": call.name, "arguments": arguments},
    }


def _to_api_tool(tool: ToolDefinition) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": dict(tool.parameters),
        },
    }


# ---- API -> our types ---------------------------------------------------------


def _from_api_completion(completion: ChatCompletion) -> ModelResponse:
    if not completion.choices:
        raise LanguageModelError("The model returned no choices.")
    message = completion.choices[0].message

    tool_calls = tuple(
        _from_api_tool_call(call.id, call.function.name, call.function.arguments)
        for call in message.tool_calls or ()
        if call.type == "function"
    )
    usage = completion.usage
    return ModelResponse(
        text=message.content or "",
        tool_calls=tool_calls,
        usage=TokenUsage(
            input_tokens=(usage.prompt_tokens or 0) if usage else 0,
            output_tokens=(usage.completion_tokens or 0) if usage else 0,
        ),
    )


def _from_api_tool_call(call_id: str, name: str, raw_arguments: str) -> ToolCall:
    try:
        arguments = json.loads(raw_arguments) if raw_arguments.strip() else {}
    except json.JSONDecodeError:
        arguments = None
    if not isinstance(arguments, dict):
        return ToolCall(id=call_id, name=name, arguments={}, invalid_arguments=raw_arguments)
    return ToolCall(id=call_id, name=name, arguments=arguments)
