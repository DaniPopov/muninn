"""The agent's own types. Every LLM provider adapter maps to and from these.

No SDK types here on purpose: the harness and the tools only ever see these classes,
so adding a provider never changes them. See docs/architecture/agent.md.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from app.domain.agent.exceptions import InvalidMessageError, InvalidToolDefinitionError

# The tool-name format OpenAI and Anthropic both accept.
_TOOL_NAME = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")


class Role(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass(frozen=True)
class ToolCall:
    """The model asking us to run one tool."""

    id: str  # the provider's id; we send it back with the result
    name: str
    arguments: Mapping[str, Any]  # already parsed from JSON by the adapter


@dataclass(frozen=True)
class Message:
    """One message in the conversation sent to the model.

    Use the constructors (Message.user(...), Message.tool_result(...)) rather than
    building one by hand: they make the rules below hard to get wrong.
    """

    role: Role
    content: str = ""
    tool_calls: tuple[ToolCall, ...] = ()  # only on ASSISTANT messages
    tool_call_id: str | None = None  # only on TOOL messages

    def __post_init__(self) -> None:
        if self.tool_calls and self.role is not Role.ASSISTANT:
            raise InvalidMessageError("Only assistant messages can contain tool calls.")
        if self.role is Role.TOOL and not self.tool_call_id:
            raise InvalidMessageError("A tool message must say which tool call it answers.")
        if self.tool_call_id and self.role is not Role.TOOL:
            raise InvalidMessageError("Only tool messages can answer a tool call.")
        if self.role is not Role.ASSISTANT and not self.content:
            raise InvalidMessageError(f"A {self.role} message can't be empty.")
        if self.role is Role.ASSISTANT and not self.content and not self.tool_calls:
            raise InvalidMessageError("An assistant message needs text or tool calls.")

    @classmethod
    def system(cls, content: str) -> Message:
        return cls(Role.SYSTEM, content)

    @classmethod
    def user(cls, content: str) -> Message:
        return cls(Role.USER, content)

    @classmethod
    def assistant(cls, content: str = "", tool_calls: tuple[ToolCall, ...] = ()) -> Message:
        return cls(Role.ASSISTANT, content, tool_calls=tool_calls)

    @classmethod
    def tool_result(cls, tool_call_id: str, content: str) -> Message:
        return cls(Role.TOOL, content, tool_call_id=tool_call_id)


@dataclass(frozen=True)
class ToolDefinition:
    """What the model is told about a tool: its name, what it's for, its arguments."""

    name: str
    description: str
    parameters: Mapping[str, Any]  # JSON Schema of the arguments

    def __post_init__(self) -> None:
        if not _TOOL_NAME.match(self.name):
            raise InvalidToolDefinitionError(
                f"Tool name {self.name!r} must be 1-64 letters, digits, '_' or '-'."
            )
        if not self.description.strip():
            raise InvalidToolDefinitionError(f"Tool {self.name!r} needs a description.")


@dataclass(frozen=True)
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0

    def __post_init__(self) -> None:
        if self.input_tokens < 0 or self.output_tokens < 0:
            raise ValueError("Token counts can't be negative.")

    def __add__(self, other: TokenUsage) -> TokenUsage:
        return TokenUsage(
            self.input_tokens + other.input_tokens,
            self.output_tokens + other.output_tokens,
        )

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass(frozen=True)
class ModelResponse:
    """What one model call returned: text, tool calls, or (rarely) both."""

    text: str = ""
    tool_calls: tuple[ToolCall, ...] = ()
    usage: TokenUsage = TokenUsage()

    @property
    def wants_tools(self) -> bool:
        return bool(self.tool_calls)

    def as_message(self) -> Message:
        """This response as the assistant message to append to the conversation."""
        return Message.assistant(self.text, self.tool_calls)
