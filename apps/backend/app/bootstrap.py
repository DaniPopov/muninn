"""Composition root: the one place that knows which adapters we use.

It reads Settings, creates adapters (database, WhatsApp, speech-to-text, ...), builds
the services on top of them, and closes everything on shutdown. It's also the only
module allowed to import from `app.adapters`. See docs/architecture/backend.md.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from app.config import Settings


@dataclass(frozen=True)
class Container:
    """Everything the API layer can ask for. Services get added here feature by feature."""

    settings: Settings


@asynccontextmanager
async def build_container(settings: Settings) -> AsyncIterator[Container]:
    # Adapters that hold connections (DB engine, HTTP clients, the Whisper model) will be
    # opened here, before the yield, and closed after it.
    yield Container(settings=settings)
