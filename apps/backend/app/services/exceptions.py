"""Base error categories for the services layer. See app/domain/exceptions.py for the idea."""

from __future__ import annotations


class ServiceError(Exception):
    code: str = "service_error"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code


class NotFoundError(ServiceError):
    code = "not_found"


class ConflictError(ServiceError):
    code = "conflict"


class UnavailableError(ServiceError):
    """An outside system we depend on (WhatsApp, LLM, STT) is down or timing out."""

    code = "unavailable"
