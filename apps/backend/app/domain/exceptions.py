"""Base error categories for the domain layer.

Features subclass these (e.g. `InvalidReminderTimeError(ValidationError)`), and
`api/errors.py` maps each category to an HTTP status once, for every feature.
"""

from __future__ import annotations


class DomainError(Exception):
    """A business rule was broken. `code` is machine-readable, `message` is for humans."""

    code: str = "domain_error"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code


class ValidationError(DomainError):
    """Input is well-formed but not allowed (empty memory, reminder in the past, ...)."""

    code = "validation_error"
