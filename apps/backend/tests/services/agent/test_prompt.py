from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from app.services.agent.prompt import SystemPrompt


def test_render_fills_time_in_the_users_timezone() -> None:
    prompt = SystemPrompt("Now: {now}\nZone: {timezone}")

    text = prompt.render(
        now=datetime(2026, 9, 25, 7, 0, tzinfo=UTC), timezone=ZoneInfo("Asia/Jerusalem")
    )

    assert text == "Now: Friday, 2026-09-25 10:00\nZone: Asia/Jerusalem"


def test_other_braces_in_the_prompt_are_left_alone() -> None:
    prompt = SystemPrompt('Reply as JSON like {"ok": true}. Now: {now}')

    text = prompt.render(now=datetime(2026, 9, 25, 7, 0, tzinfo=UTC), timezone=ZoneInfo("UTC"))

    assert text.startswith('Reply as JSON like {"ok": true}.')


def test_the_real_system_prompt_loads_and_has_its_placeholders() -> None:
    prompt = SystemPrompt.load()

    text = prompt.render(
        now=datetime(2026, 9, 25, 7, 0, tzinfo=UTC), timezone=ZoneInfo("Asia/Jerusalem")
    )

    assert "Muninn" in text
    assert "Friday, 2026-09-25 10:00" in text
    assert "{now}" not in text
    assert "{timezone}" not in text
