from __future__ import annotations

from datetime import UTC, datetime

from app.domain.clock import Clock


class SystemClock(Clock):
    """The real clock. Tests use a fixed clock instead."""

    def now(self) -> datetime:
        return datetime.now(UTC)
