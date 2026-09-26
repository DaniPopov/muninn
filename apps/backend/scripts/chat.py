"""Talk to Muninn's agent in the terminal, before WhatsApp exists.

Uses the real model from .env (LLM_*), the real harness, and a few DEMO tools that live
only in this script. In DEV every step is printed, so you can watch the loop work.

    cd apps/backend && uv run python scripts/chat.py        (or: make chat)
    uv run python scripts/chat.py --timezone Europe/Moscow

Commands: /reset clears the conversation and notes, /quit exits (or Ctrl+D).
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, Field

from app.bootstrap import build_clock, build_language_model
from app.config import Settings
from app.domain.agent.models import Message
from app.domain.clock import Clock
from app.services.agent.exceptions import AgentError, AgentUnavailableError
from app.services.agent.harness import AgentHarness
from app.services.agent.prompt import SystemPrompt
from app.services.agent.tools import Tool, ToolRegistry

DIM, BOLD, RESET = "\033[2m", "\033[1m", "\033[0m"


# ---- DEMO tools: stand-ins until the real memories feature exists ---------------


class NoArgs(BaseModel):
    pass


class GetCurrentTimeTool(Tool[NoArgs]):
    name = "get_current_time"
    description = "Get the current date and time in the user's timezone."
    args_model = NoArgs

    def __init__(self, clock: Clock, timezone: ZoneInfo) -> None:
        self._clock = clock
        self._timezone = timezone

    async def run(self, args: NoArgs) -> str:
        return self._clock.now().astimezone(self._timezone).strftime("%A, %Y-%m-%d %H:%M")


class SaveNoteArgs(BaseModel):
    text: str = Field(description="What to remember, in the user's own words")


class SaveNoteTool(Tool[SaveNoteArgs]):
    name = "save_note"
    description = "Save something the user wants remembered."
    args_model = SaveNoteArgs

    def __init__(self, notes: list[str]) -> None:
        self._notes = notes

    async def run(self, args: SaveNoteArgs) -> str:
        self._notes.append(args.text)
        return f"Saved note #{len(self._notes)}."


class SearchNotesArgs(BaseModel):
    query: str = Field(description="Words to look for, e.g. 'passport' or 'Guy'")


class SearchNotesTool(Tool[SearchNotesArgs]):
    name = "search_notes"
    description = (
        "Search saved notes. Returns every note containing any of the words. "
        "Use it before answering questions about what the user told you."
    )
    args_model = SearchNotesArgs

    def __init__(self, notes: list[str]) -> None:
        self._notes = notes

    async def run(self, args: SearchNotesArgs) -> str:
        words = args.query.casefold().split()
        found = [n for n in self._notes if any(w in n.casefold() for w in words)]
        if not found:
            return "No matching notes." if self._notes else "No notes saved yet."
        return "\n".join(f"- {n}" for n in found)


# ---- the chat loop ------------------------------------------------------------------


def _configure_logging(verbose: bool) -> None:
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter(f"{DIM}  %(message)s{RESET}"))
    agent_logger = logging.getLogger("app.services.agent")
    agent_logger.addHandler(handler)
    agent_logger.setLevel(logging.DEBUG if verbose else logging.WARNING)
    agent_logger.propagate = False


async def chat(timezone: ZoneInfo, verbose: bool) -> None:
    settings = Settings()
    try:
        model = build_language_model(settings)
    except ValueError as exc:  # e.g. LLM_MODEL not set
        sys.exit(f"Can't start: {exc}")

    clock = build_clock()
    notes: list[str] = []
    tools = ToolRegistry(
        [GetCurrentTimeTool(clock, timezone), SaveNoteTool(notes), SearchNotesTool(notes)]
    )
    harness = AgentHarness(
        model,
        tools,
        SystemPrompt.load(),
        clock,
        timezone,
        log_content=verbose,
    )
    history: list[Message] = []

    print(f"{BOLD}Muninn{RESET} · model {model.model_name} · {timezone.key} · /reset /quit")
    while True:
        try:
            text = (await asyncio.to_thread(input, f"\n{BOLD}you>{RESET} ")).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not text:
            continue
        if text == "/quit":
            return
        if text == "/reset":
            history.clear()
            notes.clear()
            print(f"{DIM}  conversation and notes cleared{RESET}")
            continue

        started = datetime.now()
        try:
            result = await harness.run_turn(text, history)
        except (AgentUnavailableError, AgentError) as exc:
            print(f"{BOLD}muninn>{RESET} [{exc.code}] {exc.message}")
            continue

        history.extend(result.new_messages)
        seconds = (datetime.now() - started).total_seconds()
        print(f"{BOLD}muninn>{RESET} {result.reply}")
        print(
            f"{DIM}  {result.steps} step(s) · {result.usage.input_tokens} in / "
            f"{result.usage.output_tokens} out tokens · {seconds:.1f}s{RESET}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Chat with Muninn's agent in the terminal.")
    parser.add_argument("--timezone", default="Asia/Jerusalem", help="IANA timezone name")
    parser.add_argument("--quiet", action="store_true", help="don't print the agent's steps")
    args = parser.parse_args()

    try:
        timezone = ZoneInfo(args.timezone)
    except ZoneInfoNotFoundError:
        sys.exit(f"Unknown timezone: {args.timezone}")

    verbose = not args.quiet
    _configure_logging(verbose)
    asyncio.run(chat(timezone, verbose))


if __name__ == "__main__":
    main()
