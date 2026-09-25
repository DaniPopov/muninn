"""GET /health: is the process up? Used by Docker's HEALTHCHECK and uptime monitors.

It's unversioned (not under /api/v1) because it's for machines, not API clients,
and must never change shape.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from fastapi import APIRouter
from pydantic import BaseModel

from app.api.deps import SettingsDep
from app.config import AppEnv

router = APIRouter(tags=["health"])


class HealthRead(BaseModel):
    status: str
    env: AppEnv
    version: str


def _app_version() -> str:
    try:
        return version("muninn-backend")
    except PackageNotFoundError:
        return "0.0.0"


@router.get("/health")
async def health(settings: SettingsDep) -> HealthRead:
    return HealthRead(status="ok", env=settings.app_env, version=_app_version())
