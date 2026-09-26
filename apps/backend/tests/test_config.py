from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.config import AppEnv, Settings
from tests.conftest import make_settings


def test_defaults_are_safe_for_local_dev() -> None:
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.app_env is AppEnv.DEV
    assert settings.app_domain == "localhost"


def test_reads_app_env_and_domain_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "PROD")
    monkeypatch.setenv("APP_DOMAIN", "muninn.example.com")
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.app_env is AppEnv.PROD
    assert settings.app_domain == "muninn.example.com"


@pytest.mark.parametrize("raw", ["dev", " Dev ", "DEV"])
def test_app_env_is_case_insensitive(raw: str) -> None:
    assert make_settings(app_env=raw).app_env is AppEnv.DEV


def test_unknown_app_env_is_rejected() -> None:
    with pytest.raises(ValidationError):
        make_settings(app_env="PRODUCTION")


@pytest.mark.parametrize("bad", ["", "https://muninn.example.com", "muninn.example.com/"])
def test_app_domain_must_be_a_bare_domain(bad: str) -> None:
    with pytest.raises(ValidationError):
        make_settings(app_domain=bad)


@pytest.mark.parametrize(
    ("env", "docs_enabled"),
    [(AppEnv.DEV, True), (AppEnv.STAGE, True), (AppEnv.PROD, False)],
)
def test_docs_are_off_only_in_prod(env: AppEnv, docs_enabled: bool) -> None:
    assert make_settings(app_env=env).docs_enabled is docs_enabled


def test_public_url_uses_https_for_real_domains() -> None:
    assert make_settings(app_domain="localhost").public_url == "http://localhost"
    assert make_settings(app_domain="muninn.example.com").public_url == "https://muninn.example.com"


def test_finds_the_repo_root_env_file_without_counting_folders() -> None:
    from app.config import _find_root_env_file

    env_file = _find_root_env_file()
    assert env_file is not None
    assert (env_file.parent / ".env.example").is_file()
    assert (env_file.parent / "apps" / "backend").is_dir()


def test_llm_defaults_point_at_openai_with_no_key() -> None:
    settings = make_settings()
    assert settings.llm_base_url == "https://api.openai.com/v1"
    assert settings.llm_model == ""
    assert settings.llm_api_key is None


def test_empty_llm_api_key_means_no_key() -> None:
    assert make_settings(llm_api_key="  ").llm_api_key is None


def test_llm_api_key_never_prints() -> None:
    settings = make_settings(llm_api_key="sk-test-123")

    assert settings.llm_api_key is not None
    assert settings.llm_api_key.get_secret_value() == "sk-test-123"
    assert "sk-test-123" not in repr(settings)
    assert "sk-test-123" not in str(settings.llm_api_key)
