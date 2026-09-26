"""Tools: functions the model can ask us to run.

A tool is a small class with a name, a description the model reads, a Pydantic model
for its arguments, and `run()`. It gets the services it needs through its constructor,
so it stays a thin wrapper around an existing use-case. See docs/architecture/agent.md#tools.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from app.domain.agent.models import ToolCall, ToolDefinition
from app.domain.exceptions import DomainError
from app.services.agent.exceptions import DuplicateToolError
from app.services.exceptions import ServiceError

logger = logging.getLogger(__name__)


class Tool[ArgsT: BaseModel](ABC):
    """Base class for every tool. Subclasses set the three class attributes and run()."""

    name: str
    description: str
    args_model: type[ArgsT]

    @abstractmethod
    async def run(self, args: ArgsT) -> str:
        """Do the work. Return text for the model (not for the user)."""

    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=self.description,
            parameters=self.args_model.model_json_schema(),
        )


@dataclass(frozen=True)
class ToolOutcome:
    """What running one tool call produced. `content` always goes back to the model."""

    content: str
    ok: bool


class ToolRegistry:
    """The tools one harness can use, looked up by name."""

    def __init__(self, tools: Sequence[Tool[Any]]) -> None:
        self._tools: dict[str, Tool[Any]] = {}
        for tool in tools:
            if tool.name in self._tools:
                raise DuplicateToolError(f"Two tools are named {tool.name!r}.")
            self._tools[tool.name] = tool

    def definitions(self) -> list[ToolDefinition]:
        return [tool.definition() for tool in self._tools.values()]

    async def execute(self, call: ToolCall) -> ToolOutcome:
        """Run one tool call. Never raises for the model's mistakes or a failing tool.

        Errors go back to the model as "error: ..." so it can fix its call or explain
        the problem to the user, instead of the whole turn crashing.
        """
        tool = self._tools.get(call.name)
        if tool is None:
            return ToolOutcome(f"error: no tool named {call.name!r}", ok=False)

        try:
            args = tool.args_model.model_validate(dict(call.arguments))
        except PydanticValidationError as exc:
            return ToolOutcome(f"error: invalid arguments: {_describe(exc)}", ok=False)

        try:
            content = await tool.run(args)
        except (DomainError, ServiceError) as exc:
            # Our own errors carry a message written for humans; the model can use it.
            return ToolOutcome(f"error: {exc.message}", ok=False)
        except Exception:
            # Anything else is a bug. Details go to our log, never to the model.
            logger.exception("tool %s failed", call.name)
            return ToolOutcome("error: the tool failed", ok=False)

        return ToolOutcome(content or "(no output)", ok=True)


def _describe(exc: PydanticValidationError) -> str:
    """Short, model-readable version of a Pydantic error: 'text: Field required'."""
    parts = []
    for error in exc.errors():
        where = ".".join(str(part) for part in error["loc"]) or "arguments"
        parts.append(f"{where}: {error['msg']}")
    return "; ".join(parts)
