"""Turn exceptions into HTTP responses, in one place.

Features never raise HTTPException for business failures. They raise a category from
domain/ or services/, and this module decides the status code. Every error body has
the same shape:  {"error": {"code": "...", "message": "..."}}
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.domain.exceptions import DomainError, ValidationError
from app.services.exceptions import (
    ConflictError,
    NotFoundError,
    ServiceError,
    UnavailableError,
)

logger = logging.getLogger(__name__)

# Most specific first: the first matching class wins.
_STATUS_BY_CATEGORY: list[tuple[type[Exception], int]] = [
    (ValidationError, status.HTTP_422_UNPROCESSABLE_CONTENT),
    (NotFoundError, status.HTTP_404_NOT_FOUND),
    (ConflictError, status.HTTP_409_CONFLICT),
    (UnavailableError, status.HTTP_503_SERVICE_UNAVAILABLE),
    (DomainError, status.HTTP_400_BAD_REQUEST),
    (ServiceError, status.HTTP_500_INTERNAL_SERVER_ERROR),
]


def error_body(code: str, message: str) -> dict[str, dict[str, str]]:
    return {"error": {"code": code, "message": message}}


def status_for(exc: Exception) -> int:
    for category, http_status in _STATUS_BY_CATEGORY:
        if isinstance(exc, category):
            return http_status
    return status.HTTP_500_INTERNAL_SERVER_ERROR


async def _handle_known_error(request: Request, exc: Exception) -> JSONResponse:
    # Registered only for DomainError and ServiceError, which both carry code + message.
    code = getattr(exc, "code", "error")
    message = getattr(exc, "message", str(exc))
    http_status = status_for(exc)
    if http_status >= 500:
        logger.exception("request failed: %s %s", request.method, request.url.path)
    return JSONResponse(status_code=http_status, content=error_body(code, message))


async def _handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    # Log the details for us; never leak internals (stack traces, SQL) to the client.
    logger.exception("unhandled error: %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_body("internal_error", "Something went wrong on our side."),
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, _handle_known_error)
    app.add_exception_handler(ServiceError, _handle_known_error)
    app.add_exception_handler(Exception, _handle_unexpected_error)
