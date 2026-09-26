"""Composition root: the one place that knows which adapters we use.

It reads Settings, creates adapters (database, WhatsApp, speech-to-text, ...), builds
the services on top of them, and closes everything on shutdown. It's also the only
module allowed to import from `app.adapters`. See docs/architecture/backend.md.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from app.adapters.clock.system import SystemClock
from app.adapters.llm.openai_compatible import OpenAICompatibleLanguageModel
from app.config import Settings
from app.domain.agent.ports import LanguageModel
from app.domain.clock import Clock


@dataclass(frozen=True)
class Container:
    """Everything the API layer can ask for. Services get added here feature by feature."""

    settings: Settings


@asynccontextmanager
async def build_container(settings: Settings) -> AsyncIterator[Container]:
    # Adapters that hold connections (DB engine, HTTP clients, the Whisper model) will be
    # opened here, before the yield, and closed after it.
    yield Container(settings=settings)


def build_language_model(settings: Settings) -> LanguageModel:
    """The LanguageModel adapter for the configured provider (ADR 0007: OpenAI-compatible first)."""
    return OpenAICompatibleLanguageModel.create(
        base_url=settings.llm_base_url,
        model=settings.llm_model,
        api_key=settings.llm_api_key.get_secret_value() if settings.llm_api_key else None,
        reasoning_effort=settings.llm_reasoning_effort,
    )


def build_clock() -> Clock:
    return SystemClock()
