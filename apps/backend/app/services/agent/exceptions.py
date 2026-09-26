from __future__ import annotations

from app.services.exceptions import ServiceError, UnavailableError


class AgentUnavailableError(UnavailableError):
    """The model can't be reached or the turn took too long. Worth trying again later."""

    code = "agent_unavailable"


class AgentError(ServiceError):
    """The turn failed in a way retrying won't fix (e.g. the provider rejected the request)."""

    code = "agent_failed"


class DuplicateToolError(ServiceError):
    code = "duplicate_tool"
