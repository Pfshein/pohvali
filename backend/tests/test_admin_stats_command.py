import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from sqlalchemy import Date, DateTime, Integer, Uuid

from app.api.dependencies import get_db_session, get_reply_sender
from app.core.config import Settings, get_settings
from app.main import app
from app.modules.admin_stats.models import UserActivityDay
from app.modules.admin_stats.service import PeriodStats, StatsSnapshot
from app.modules.bot.stats import (
    StatsCommand,
    StatsCommandRefused,
    extract_stats_actor_id,
    format_stats,
    parse_stats_command,
)


def _update(text: str = "/stats", *, chat_type: str = "private", actor: object = 700) -> dict:
    message = {
        "chat": {"id": 700, "type": chat_type},
        "text": text,
    }
    if actor is not None:
        message["from"] = {"id": actor}
    return {"message": message}


def test_stats_parser_accepts_default_mention_and_30_days() -> None:
    assert extract_stats_actor_id(_update(" /stats@BotName 30 ")) == 700
    assert parse_stats_command(_update(), authorized=True) == StatsCommand(chat_id=700)
    assert parse_stats_command(_update("/stats@BotName 30"), authorized=True) == StatsCommand(
        chat_id=700, days=30
    )


def test_stats_parser_rejects_malformed_or_non_private_updates() -> None:
    for update in (
        _update("/statss"),
        _update("/stats", actor="700"),
        _update("/stats", chat_type="group"),
        {"message": {"chat": {"id": 700, "type": "private"}, "caption": "/stats"}},
    ):
        assert extract_stats_actor_id(update) is None
    assert parse_stats_command(_update("/statss"), authorized=True) is None
    assert parse_stats_command(_update("/stats", chat_type="group"), authorized=True) is None


def test_stats_parser_denies_before_admin_grammar_and_admin_gets_usage() -> None:
    invalid = _update("/stats 14")
    assert parse_stats_command(invalid, authorized=False) == StatsCommandRefused(
        700, "Эта команда доступна только администратору сервиса."
    )
    refused = parse_stats_command(invalid, authorized=True)
    assert isinstance(refused, StatsCommandRefused)
    assert refused.text == "Формат: /stats или /stats 30"


def test_stats_formatter_has_exact_blocks_zero_conversion_and_rounding() -> None:
    snapshot = StatsSnapshot(
        today=PeriodStats(0, 0, 0),
        last_7_days=PeriodStats(3, 1, 2),
        last_30_days=PeriodStats(3, 1, 2),
        all_time=PeriodStats(6, 2, 4),
    )
    rendered = format_stats(snapshot)
    assert "Сегодня (UTC)" in rendered
    assert "Последние 7 дней (UTC)" in rendered
    assert "За всё время" in rendered
    assert "• Конверсия: 0,0%" in rendered
    assert "• Конверсия: 33,3%" in rendered
    assert "Telegram" not in rendered
    thirty = format_stats(snapshot, days=30)
    assert "Последние 30 дней (UTC)" in thirty
    assert "Сегодня (UTC)" not in thirty


def test_activity_model_has_only_aggregate_columns_and_required_constraints() -> None:
    table = UserActivityDay.__table__
    assert set(table.columns) == {
        table.c.user_id,
        table.c.activity_date,
        table.c.first_opened_at,
        table.c.last_opened_at,
        table.c.open_count,
    }
    assert isinstance(table.c.user_id.type, Uuid)
    assert isinstance(table.c.activity_date.type, Date)
    assert isinstance(table.c.first_opened_at.type, DateTime)
    assert table.c.first_opened_at.type.timezone is True
    assert isinstance(table.c.last_opened_at.type, DateTime)
    assert isinstance(table.c.open_count.type, Integer)
    assert {column.name for column in table.primary_key.columns} == {
        "user_id",
        "activity_date",
    }
    foreign_key = next(iter(table.c.user_id.foreign_keys))
    assert foreign_key.column.table.name == "users"
    assert foreign_key.ondelete == "CASCADE"
    assert any(
        constraint.name == "ck_user_activity_days_open_count_positive"
        for constraint in table.constraints
    )
    assert {tuple(column.name for column in index.columns) for index in table.indexes} == {
        ("activity_date",)
    }
    assert set(table.columns).isdisjoint({"telegram_id", "body", "payload", "event_data"})


class _Sender:
    def __init__(self) -> None:
        self.replies = []

    async def __call__(self, reply) -> None:
        self.replies.append(reply)


async def _session_override():
    yield SimpleNamespace()


def _client() -> tuple[TestClient, _Sender]:
    sender = _Sender()
    app.dependency_overrides[get_settings] = lambda: Settings(
        app_domain="https://app.example.com",
        telegram_webhook_path="secret",
        telegram_webhook_secret="header",
    )
    app.dependency_overrides[get_reply_sender] = lambda: sender
    app.dependency_overrides[get_db_session] = _session_override
    return TestClient(app), sender


def teardown_function() -> None:
    app.dependency_overrides.pop(get_settings, None)
    app.dependency_overrides.pop(get_reply_sender, None)
    app.dependency_overrides.pop(get_db_session, None)


def test_stats_webhook_admin_default_and_30_day_reply() -> None:
    client, sender = _client()
    snapshot = StatsSnapshot(
        PeriodStats(1, 1, 1), PeriodStats(2, 1, 2), PeriodStats(3, 1, 3), PeriodStats(4, 1, 4)
    )
    with (
        patch("app.api.v1.telegram.is_admin_user", new=AsyncMock(return_value=True)),
        patch(
            "app.api.v1.telegram.get_stats_snapshot", new=AsyncMock(return_value=snapshot)
        ) as stats,
    ):
        response = client.post(
            "/api/v1/telegram/secret",
            headers={"X-Telegram-Bot-Api-Secret-Token": "header"},
            json=_update("/stats"),
        )
        response_30 = client.post(
            "/api/v1/telegram/secret",
            headers={"X-Telegram-Bot-Api-Secret-Token": "header"},
            json=_update("/stats 30"),
        )
    assert response.status_code == response_30.status_code == 200
    assert len(sender.replies) == 2
    assert "Сегодня (UTC)" in sender.replies[0].text
    assert "Последние 30 дней (UTC)" in sender.replies[1].text
    assert stats.await_count == 2


def test_stats_webhook_user_and_unknown_get_same_denial_without_stats_query() -> None:
    client, sender = _client()
    with (
        patch("app.api.v1.telegram.is_admin_user", new=AsyncMock(return_value=False)) as auth,
        patch("app.api.v1.telegram.get_stats_snapshot", new=AsyncMock()) as stats,
    ):
        for actor in (42, 404):
            response = client.post(
                "/api/v1/telegram/secret",
                headers={"X-Telegram-Bot-Api-Secret-Token": "header"},
                json={**_update(actor=actor), "update_id": actor},
            )
            assert response.status_code == 200
    assert [reply.text for reply in sender.replies] == [
        "Эта команда доступна только администратору сервиса."
    ] * 2
    assert auth.await_count == 2
    stats.assert_not_awaited()


def test_stats_webhook_group_is_ignored_without_role_lookup() -> None:
    client, sender = _client()
    with patch("app.api.v1.telegram.is_admin_user", new=AsyncMock()) as auth:
        response = client.post(
            "/api/v1/telegram/secret",
            headers={"X-Telegram-Bot-Api-Secret-Token": "header"},
            json=_update(chat_type="supergroup"),
        )
    assert response.status_code == 200
    assert sender.replies == []
    auth.assert_not_awaited()


def test_stats_webhook_hides_service_failure_and_logs_only_outcome(caplog) -> None:
    client, sender = _client()
    with (
        patch("app.api.v1.telegram.is_admin_user", new=AsyncMock(return_value=True)),
        patch(
            "app.api.v1.telegram.get_stats_snapshot",
            new=AsyncMock(side_effect=RuntimeError("secret praise data")),
        ),
        caplog.at_level(logging.INFO),
    ):
        response = client.post(
            "/api/v1/telegram/secret",
            headers={"X-Telegram-Bot-Api-Secret-Token": "header"},
            json=_update("/stats"),
        )
    assert response.status_code == 200
    assert len(sender.replies) == 1
    assert "Не удалось получить статистику" in sender.replies[0].text
    assert "secret praise data" not in caplog.text
    assert "700" not in caplog.text
