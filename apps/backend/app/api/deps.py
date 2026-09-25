"""FastAPI dependencies: how routers get what they need from the Container.

Routers declare `settings: SettingsDep` and FastAPI fills it in. Services get the same
treatment as they're added (`MemoryServiceDep`, ...).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from app.bootstrap import Container
from app.config import Settings


def get_container(request: Request) -> Container:
    container: Container = request.app.state.container
    return container


def get_settings(container: Annotated[Container, Depends(get_container)]) -> Settings:
    return container.settings


SettingsDep = Annotated[Settings, Depends(get_settings)]
