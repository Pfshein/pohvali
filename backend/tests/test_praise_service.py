from datetime import UTC, date, datetime

from app.modules.praises.service import local_date_in_timezone


def test_local_date_uses_the_users_timezone_not_utc() -> None:
    just_after_utc_midnight = datetime(2026, 9, 1, 0, 30, tzinfo=UTC)

    assert local_date_in_timezone("Europe/Moscow", just_after_utc_midnight) == date(2026, 9, 1)
    assert local_date_in_timezone("America/New_York", just_after_utc_midnight) == date(2026, 8, 31)


def test_local_date_falls_back_cleanly_for_utc() -> None:
    moment = datetime(2026, 9, 1, 23, 59, tzinfo=UTC)

    assert local_date_in_timezone("UTC", moment) == date(2026, 9, 1)
