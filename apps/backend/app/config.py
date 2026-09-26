"""Application settings, read from environment variables.

One `.env` at the repo root feeds both Docker Compose and the backend. Inside Docker,
Compose passes the values as real environment variables; when running locally we read
the root `.env` directly. Environment variables always win over the file.
"""

from __future__ import annotations

from enum import StrEnum
from functools import cached_property
from pathlib import Path

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _find_root_env_file() -> Path | None:
    """The repo root's .env when running from a checkout, None inside Docker.

    We walk up from this file until we find `.env.example`, which only exists at the
    repo root. No counting of folder levels, so moving files around can't break it.
    The Docker image doesn't contain `.env.example`: there, Compose passes config as
    real environment variables and there's no file to read.
    """
    for directory in Path(__file__).resolve().parents:
        if (directory / ".env.example").is_file():
            return directory / ".env"
    return None


# The values OpenAI-compatible APIs accept for `reasoning_effort`.
REASONING_EFFORTS = ("none", "minimal", "low", "medium", "high", "xhigh", "max")


class AppEnv(StrEnum):
    """Where the app is running. See docs/architecture/backend.md#configuration-and-environments."""

    DEV = "DEV"
    STAGE = "STAGE"
    PROD = "PROD"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_find_root_env_file(),
        env_file_encoding="utf-8",
        # The root .env also holds keys for Compose (ports, ...). They aren't ours.
        extra="ignore",
    )

    app_env: AppEnv = AppEnv.DEV
    app_domain: str = "localhost"

    # LLM (ADR 0007). Any server that speaks the OpenAI chat API.
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = ""
    # SecretStr: prints as '**********', so the key can't leak into logs or errors.
    llm_api_key: SecretStr | None = None
    # Optional. Sent only when set. OpenAI's GPT-6 models need "none" for tool calling
    # over Chat Completions. Leave empty for servers that don't support it (Ollama, ...).
    llm_reasoning_effort: str | None = None

    @field_validator("llm_api_key", "llm_reasoning_effort", mode="before")
    @classmethod
    def _empty_means_not_set(cls, value: object) -> object:
        # `LLM_API_KEY=` in .env means "not set" (local models don't need a key).
        return None if isinstance(value, str) and not value.strip() else value

    @field_validator("llm_reasoning_effort")
    @classmethod
    def _known_reasoning_effort(cls, value: str | None) -> str | None:
        # Fail at startup on a typo, not on the first user message.
        if value is None:
            return None
        effort = value.strip().lower()
        if effort not in REASONING_EFFORTS:
            allowed = ", ".join(REASONING_EFFORTS)
            raise ValueError(f"LLM_REASONING_EFFORT must be one of: {allowed}")
        return effort

    @field_validator("app_env", mode="before")
    @classmethod
    def _normalize_env(cls, value: object) -> object:
        # Accept "dev" as well as "DEV"; people will type both.
        return value.strip().upper() if isinstance(value, str) else value

    @field_validator("app_domain")
    @classmethod
    def _bare_domain(cls, value: str) -> str:
        # We build URLs from the domain ourselves, so it must be just the host.
        domain = value.strip()
        if not domain:
            raise ValueError("APP_DOMAIN must not be empty")
        if "://" in domain or "/" in domain:
            raise ValueError("APP_DOMAIN must be a bare domain like 'muninn.example.com'")
        return domain

    @property
    def is_dev(self) -> bool:
        return self.app_env is AppEnv.DEV

    @property
    def is_prod(self) -> bool:
        return self.app_env is AppEnv.PROD

    @property
    def docs_enabled(self) -> bool:
        """Swagger UI (/docs) is a debugging tool. PROD doesn't expose it."""
        return not self.is_prod

    @cached_property
    def public_url(self) -> str:
        """Base URL the outside world uses to reach us (e.g. for the WhatsApp webhook)."""
        scheme = "http" if self.app_domain == "localhost" else "https"
        return f"{scheme}://{self.app_domain}"
