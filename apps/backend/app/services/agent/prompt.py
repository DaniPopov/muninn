"""The system prompt: a file in prompts/, with a few placeholders filled on every turn.

Prompts are files so they're reviewed in pull requests like code. We fill placeholders
with plain replace() instead of str.format(), so braces in the prompt text are safe.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

PROMPTS_DIR = Path(__file__).parent / "prompts"


class SystemPrompt:
    def __init__(self, template: str) -> None:
        self._template = template

    @classmethod
    def load(cls, name: str = "system.md") -> SystemPrompt:
        return cls((PROMPTS_DIR / name).read_text(encoding="utf-8"))

    def render(self, *, now: datetime, timezone: ZoneInfo) -> str:
        local = now.astimezone(timezone)
        return (
            self._template.replace("{now}", local.strftime("%A, %Y-%m-%d %H:%M"))
            .replace("{timezone}", timezone.key)
            .strip()
        )
