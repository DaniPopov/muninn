"""The agent harness: runs one turn of the conversation.

A turn is one user message and everything until the reply. The loop:

    ask the model  ->  it answers with text?          -> done, that's the reply
                   ->  it asks for tools?             -> run them, send the results back,
                                                         ask the model again

With a step limit (a model that never stops calling tools) and a timeout (the user is
waiting on their phone). See docs/architecture/agent.md#the-loop.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Sequence
from dataclasses import dataclass
from uuid import uuid4
from zoneinfo import ZoneInfo

from app.domain.agent.exceptions import LanguageModelError, LanguageModelUnavailableError
from app.domain.agent.models import Message, ModelResponse, Role, TokenUsage, ToolCall
from app.domain.agent.ports import LanguageModel
from app.domain.clock import Clock
from app.services.agent.exceptions import AgentError, AgentUnavailableError
from app.services.agent.prompt import SystemPrompt
from app.services.agent.tools import ToolRegistry

logger = logging.getLogger(__name__)

MAX_STEPS = 5  # a normal turn needs 1-3; more means the model is stuck
TURN_TIMEOUT_SECONDS = 30.0  # the user is waiting on their phone
MAX_HISTORY_MESSAGES = 20  # enough for follow-ups, keeps every call small and cheap
MAX_TOOL_RESULT_CHARS = 4_000  # a huge tool result must not flood the context

FALLBACK_REPLY = "Sorry, I couldn't finish that. Could you try asking in a different way?"


@dataclass(frozen=True)
class TurnResult:
    reply: str
    new_messages: tuple[Message, ...]  # the user message + everything this turn added
    steps: int
    usage: TokenUsage  # summed over all steps
    completed: bool  # False when we fell back (step limit, empty answer)


@dataclass(frozen=True)
class _LoopEnd:
    reply: str
    steps: int
    usage: TokenUsage
    completed: bool


class AgentHarness:
    """Stateless: history goes in, new messages come out. Storing them is the caller's job."""

    def __init__(
        self,
        model: LanguageModel,
        tools: ToolRegistry,
        prompt: SystemPrompt,
        clock: Clock,
        timezone: ZoneInfo,
        *,
        max_steps: int = MAX_STEPS,
        turn_timeout_seconds: float = TURN_TIMEOUT_SECONDS,
        log_content: bool = False,
    ) -> None:
        self._model = model
        self._tools = tools
        self._prompt = prompt
        self._clock = clock
        self._timezone = timezone
        self._max_steps = max_steps
        self._turn_timeout = turn_timeout_seconds
        # Message text is personal. Only DEV logs it (docs/architecture/agent.md#logging).
        self._log_content = log_content

    async def run_turn(self, user_text: str, history: Sequence[Message] = ()) -> TurnResult:
        turn_id = uuid4().hex[:12]
        started = time.perf_counter()
        system = Message.system(self._prompt.render(now=self._clock.now(), timezone=self._timezone))
        new_messages: list[Message] = [Message.user(user_text)]
        self._log_text(turn_id, "user", user_text)

        try:
            async with asyncio.timeout(self._turn_timeout):
                end = await self._loop(turn_id, [system, *trim_history(history)], new_messages)
        except TimeoutError as exc:
            logger.warning("agent.timeout turn_id=%s after_s=%s", turn_id, self._turn_timeout)
            raise AgentUnavailableError("The assistant took too long to answer.") from exc

        new_messages.append(Message.assistant(end.reply))
        self._log_finish(turn_id, started, end)
        return TurnResult(end.reply, tuple(new_messages), end.steps, end.usage, end.completed)

    async def _loop(
        self, turn_id: str, prefix: list[Message], new_messages: list[Message]
    ) -> _LoopEnd:
        """Ask the model, run the tools it wants, repeat. Appends to `new_messages`."""
        usage = TokenUsage()
        for step in range(1, self._max_steps + 1):
            response = await self._ask_model(turn_id, step, [*prefix, *new_messages])
            usage += response.usage

            if not response.wants_tools:
                if response.text:
                    return _LoopEnd(response.text, step, usage, completed=True)
                return _LoopEnd(FALLBACK_REPLY, step, usage, completed=False)

            new_messages.append(response.as_message())
            for call in response.tool_calls:
                new_messages.append(await self._run_tool(turn_id, step, call))

        # Out of steps: the model kept calling tools and never answered.
        logger.warning("agent.max_steps turn_id=%s steps=%d", turn_id, self._max_steps)
        return _LoopEnd(FALLBACK_REPLY, self._max_steps, usage, completed=False)

    async def _ask_model(self, turn_id: str, step: int, messages: list[Message]) -> ModelResponse:
        started = time.perf_counter()
        try:
            response = await self._model.complete(messages, self._tools.definitions())
        except LanguageModelUnavailableError as exc:
            logger.warning("agent.model_unavailable turn_id=%s step=%d", turn_id, step)
            raise AgentUnavailableError("The assistant is unavailable right now.") from exc
        except LanguageModelError as exc:
            logger.error("agent.model_error turn_id=%s step=%d error=%s", turn_id, step, exc)
            raise AgentError("The assistant couldn't process this message.") from exc

        logger.info(
            "agent.step turn_id=%s step=%d model=%s tool_calls=%d "
            "input_tokens=%d output_tokens=%d duration_ms=%d",
            turn_id,
            step,
            self._model.model_name,
            len(response.tool_calls),
            response.usage.input_tokens,
            response.usage.output_tokens,
            _ms_since(started),
        )
        return response

    async def _run_tool(self, turn_id: str, step: int, call: ToolCall) -> Message:
        started = time.perf_counter()
        outcome = await self._tools.execute(call)
        logger.info(
            "agent.tool turn_id=%s step=%d tool=%s ok=%s duration_ms=%d",
            turn_id,
            step,
            call.name,
            outcome.ok,
            _ms_since(started),
        )
        self._log_text(turn_id, f"tool {call.name} args={dict(call.arguments)} ->", outcome.content)
        return Message.tool_result(call.id, _truncate(outcome.content))

    def _log_finish(self, turn_id: str, started: float, end: _LoopEnd) -> None:
        logger.info(
            "agent.turn turn_id=%s steps=%d completed=%s "
            "input_tokens=%d output_tokens=%d duration_ms=%d",
            turn_id,
            end.steps,
            end.completed,
            end.usage.input_tokens,
            end.usage.output_tokens,
            _ms_since(started),
        )
        self._log_text(turn_id, "reply", end.reply)

    def _log_text(self, turn_id: str, label: str, text: str) -> None:
        if self._log_content:
            logger.debug("agent.content turn_id=%s %s %r", turn_id, label, text)


def trim_history(history: Sequence[Message], limit: int = MAX_HISTORY_MESSAGES) -> list[Message]:
    """The last `limit` messages, starting at a user message.

    Cutting blindly could start the context with a tool result whose tool call was cut
    off, which providers reject. So after cutting, we drop messages until the first one
    is from the user.
    """
    recent = list(history)[-limit:]
    while recent and recent[0].role is not Role.USER:
        recent.pop(0)
    return recent


def _truncate(text: str, limit: int = MAX_TOOL_RESULT_CHARS) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n[truncated: {len(text) - limit} more characters]"


def _ms_since(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)
