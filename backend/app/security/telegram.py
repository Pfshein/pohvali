import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qsl


class InvalidInitData(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class TelegramIdentity:
    telegram_id: int
    auth_date: datetime


def validate_init_data(
    init_data: str,
    bot_token: str,
    *,
    now: datetime | None = None,
    max_age: timedelta = timedelta(hours=24),
) -> TelegramIdentity:
    """Validate Telegram Mini App initData and return its minimal identity."""
    pairs = dict(parse_qsl(init_data, keep_blank_values=True, strict_parsing=True))
    received_hash = pairs.pop("hash", None)
    pairs.pop("signature", None)

    if not received_hash:
        raise InvalidInitData("missing hash")

    data_check_string = "\n".join(f"{key}={pairs[key]}" for key in sorted(pairs))
    secret_key = hmac.new(
        key=b"WebAppData",
        msg=bot_token.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    expected_hash = hmac.new(
        key=secret_key,
        msg=data_check_string.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected_hash, received_hash):
        raise InvalidInitData("invalid hash")

    try:
        auth_date = datetime.fromtimestamp(int(pairs["auth_date"]), tz=UTC)
        user = json.loads(pairs["user"])
        telegram_id = user["id"]
        if type(telegram_id) is not int or not 0 < telegram_id < 2**63:
            raise TypeError("telegram id must be a positive signed bigint")
    except (KeyError, TypeError, ValueError, json.JSONDecodeError, OSError) as exc:
        raise InvalidInitData("invalid payload") from exc

    checked_at = (now or datetime.now(UTC)).astimezone(UTC)
    if auth_date > checked_at + timedelta(minutes=1):
        raise InvalidInitData("auth_date is in the future")
    if checked_at - auth_date > max_age:
        raise InvalidInitData("initData expired")

    return TelegramIdentity(telegram_id=telegram_id, auth_date=auth_date)
