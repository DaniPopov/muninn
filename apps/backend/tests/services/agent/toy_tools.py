"""Small tools used to test the harness. Real tools arrive with their features."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.domain.exceptions import ValidationError
from app.services.agent.tools import Tool


class EchoArgs(BaseModel):
    text: str = Field(description="Text to echo back")


class EchoTool(Tool[EchoArgs]):
    name = "echo"
    description = "Return the text you were given."
    args_model = EchoArgs

    def __init__(self) -> None:
        self.received: list[str] = []

    async def run(self, args: EchoArgs) -> str:
        self.received.append(args.text)
        return f"echo: {args.text}"


class NoArgs(BaseModel):
    pass


class RejectingTool(Tool[NoArgs]):
    """Fails the way a real tool does when a business rule is broken."""

    name = "reject"
    description = "Always refuses."
    args_model = NoArgs

    async def run(self, args: NoArgs) -> str:
        raise ValidationError("That reminder is in the past.", code="reminder_in_past")


class CrashingTool(Tool[NoArgs]):
    """Fails the way a bug does."""

    name = "crash"
    description = "Always crashes."
    args_model = NoArgs

    async def run(self, args: NoArgs) -> str:
        raise RuntimeError("database password is hunter2")


class HugeOutputTool(Tool[NoArgs]):
    name = "huge"
    description = "Returns a very long result."
    args_model = NoArgs

    async def run(self, args: NoArgs) -> str:
        return "x" * 10_000
