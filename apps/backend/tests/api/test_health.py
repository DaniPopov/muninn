from __future__ import annotations

from collections.abc import Callable

from httpx import AsyncClient

from app.config import AppEnv, Settings
from tests.conftest import make_settings


async def test_health_reports_ok_and_environment(client: AsyncClient) -> None:
    response = await client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["env"] == "DEV"
    assert body["version"]


async def test_docs_available_outside_prod(client: AsyncClient) -> None:
    assert (await client.get("/docs")).status_code == 200
    assert (await client.get("/openapi.json")).status_code == 200


async def test_docs_hidden_in_prod(client_for: Callable[[Settings], AsyncClient]) -> None:
    async with client_for(make_settings(app_env=AppEnv.PROD)) as client:
        assert (await client.get("/docs")).status_code == 404
        assert (await client.get("/openapi.json")).status_code == 404
