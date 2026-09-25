"""FastAPI entry point.

`create_app()` is a factory: nothing is built when this module is imported. Uvicorn
calls it at startup (`uvicorn app.main:create_app --factory`) and tests call it with
their own Settings. There is no global `app` or global `settings` object on purpose:
settings reach the code through bootstrap.Container and api/deps.py.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import health
from app.api.errors import register_error_handlers
from app.api.v1.router import router as v1_router
from app.bootstrap import build_container
from app.config import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # Build adapters and services once at startup; close them on shutdown.
        async with build_container(settings) as container:
            app.state.container = container
            yield

    app = FastAPI(
        title="Muninn",
        summary="Self-hosted WhatsApp assistant that remembers things for you.",
        lifespan=lifespan,
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.docs_enabled else None,
    )
    register_error_handlers(app)
    app.include_router(health.router)
    app.include_router(v1_router)
    return app
