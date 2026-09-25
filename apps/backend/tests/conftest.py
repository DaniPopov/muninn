from __future__ import annotations

from collections.abc import AsyncIterator, Callable

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.config import AppEnv, Settings
from app.main import create_app


def make_settings(**overrides: object) -> Settings:
    """Settings for tests. `_env_file=None` so a developer's local .env can't leak in."""
    values: dict[str, object] = {"app_env": AppEnv.DEV, "app_domain": "localhost", **overrides}
    return Settings(_env_file=None, **values)  # type: ignore[call-arg]


@pytest.fixture
def settings() -> Settings:
    return make_settings()


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    return create_app(settings)


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    # ASGITransport doesn't run startup/shutdown, so we run the lifespan ourselves.
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
    ):
        yield client


@pytest.fixture
def client_for() -> Callable[[Settings], AsyncClient]:
    """Build a client for an app with custom settings (lifespan not needed for routing tests)."""

    def _make(settings: Settings) -> AsyncClient:
        return AsyncClient(
            transport=ASGITransport(app=create_app(settings)), base_url="http://test"
        )

    return _make
