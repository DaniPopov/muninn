"""Errors of the agent domain: invalid messages, and failures of the LanguageModel port.

Adapters raise the LanguageModel errors so the harness never sees an SDK exception.
"""

from __future__ import annotations

from app.domain.exceptions import DomainError, ValidationError


class InvalidMessageError(ValidationError):
    """A message breaks a rule, e.g. a TOOL message without the id of its tool call."""

    code = "invalid_message"


class InvalidToolDefinitionError(ValidationError):
    code = "invalid_tool_definition"


class LanguageModelError(DomainError):
    """The model call failed and retrying won't help (bad request, invalid response)."""

    code = "language_model_error"


class LanguageModelUnavailableError(LanguageModelError):
    """The model can't be reached right now: timeout, rate limit, 5xx, network error."""

    code = "language_model_unavailable"
