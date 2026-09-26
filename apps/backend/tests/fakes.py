"""Test doubles shared across test folders."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.domain.clock import Clock


class FixedClock(Clock):
    """A clock that only moves when the test says so."""

    def __init__(self, start: datetime | None = None) -> None:
        self._now = start or datetime(2026, 9, 25, 7, 0, tzinfo=UTC)  # Friday 10:00 in Israel

    def now(self) -> datetime:
        return self._now

    def advance(self, **delta: float) -> None:
        self._now += timedelta(**delta)
