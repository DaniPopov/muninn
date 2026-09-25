"""Every error category maps to one HTTP status and the same body shape."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.domain.exceptions import DomainError, ValidationError
from app.main import create_app
from app.services.exceptions import ConflictError, NotFoundError, UnavailableError
from tests.conftest import make_settings


def _app_raising(exc: Exception) -> FastAPI:
    app = create_app(make_settings())

    @app.get("/boom")
    async def boom() -> None:
        raise exc

    return app


@pytest.mark.parametrize(
    ("exc", "status", "code"),
    [
        (ValidationError("in the past", code="reminder_in_past"), 422, "reminder_in_past"),
        (NotFoundError("no such memory"), 404, "not_found"),
        (ConflictError("already exists"), 409, "conflict"),
        (UnavailableError("whatsapp is down"), 503, "unavailable"),
        (DomainError("rule broken"), 400, "domain_error"),
    ],
)
async def test_error_category_maps_to_status(exc: Exception, status: int, code: str) -> None:
    transport = ASGITransport(app=_app_raising(exc))
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/boom")

    assert response.status_code == status
    assert response.json() == {"error": {"code": code, "message": str(exc)}}


async def test_unexpected_error_does_not_leak_details() -> None:
    app = _app_raising(RuntimeError("db password is hunter2"))
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/boom")

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    assert "hunter2" not in response.text
