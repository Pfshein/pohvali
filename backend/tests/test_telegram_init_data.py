import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

import pytest

from app.security.telegram import InvalidInitData, validate_init_data

BOT_TOKEN = "123456:TEST-TOKEN"
NOW = datetime(2026, 8, 31, 12, tzinfo=UTC)


def signed_init_data(*, auth_date: datetime = NOW, telegram_id: object = 42) -> str:
    values = {
        "auth_date": str(int(auth_date.timestamp())),
        "query_id": "AAHdF6IQAAAAAN0XohDhrOrc",
        "user": json.dumps(
            {"id": telegram_id, "first_name": "Must not be persisted", "username": "private"},
            separators=(",", ":"),
        ),
    }
    data_check_string = "\n".join(f"{key}={values[key]}" for key in sorted(values))
    secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    values["hash"] = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()
    return urlencode(values)


def test_accepts_valid_data_and_returns_only_minimal_identity() -> None:
    identity = validate_init_data(signed_init_data(), BOT_TOKEN, now=NOW)

    assert identity.telegram_id == 42
    assert identity.auth_date == NOW
    assert not hasattr(identity, "first_name")
    assert not hasattr(identity, "username")


def test_rejects_tampered_data() -> None:
    tampered = signed_init_data().replace("%22id%22%3A42", "%22id%22%3A99")

    with pytest.raises(InvalidInitData, match="invalid hash"):
        validate_init_data(tampered, BOT_TOKEN, now=NOW)


def test_rejects_expired_data() -> None:
    old = NOW - timedelta(hours=24, seconds=1)

    with pytest.raises(InvalidInitData, match="expired"):
        validate_init_data(signed_init_data(auth_date=old), BOT_TOKEN, now=NOW)


def test_rejects_missing_hash() -> None:
    with pytest.raises(InvalidInitData, match="missing hash"):
        validate_init_data("auth_date=1", BOT_TOKEN, now=NOW)


@pytest.mark.parametrize("telegram_id", [True, "42", 42.0, 0, -1, 2**63])
def test_rejects_non_bigint_telegram_id(telegram_id: object) -> None:
    with pytest.raises(InvalidInitData, match="invalid payload"):
        validate_init_data(
            signed_init_data(telegram_id=telegram_id),
            BOT_TOKEN,
            now=NOW,
        )
