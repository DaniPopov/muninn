"""Clock port: "what time is it now?"

The agent puts the current time in its prompt (so "Tuesday at 10" can become an exact
time) and reminders fire at a time. Asking a port instead of calling datetime.now()
directly lets tests freeze time.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime


class Clock(ABC):
    @abstractmethod
    def now(self) -> datetime:
        """Current time, timezone-aware, in UTC."""
