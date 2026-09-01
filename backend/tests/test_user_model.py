from sqlalchemy import BigInteger, DateTime, String, Uuid

from app.modules.users.models import User


def test_user_model_persists_only_the_minimal_identity() -> None:
    columns = set(User.__table__.columns.keys())
    forbidden_pii = {
        "first_name",
        "last_name",
        "name",
        "username",
        "avatar",
        "avatar_url",
        "language",
        "language_code",
    }

    assert columns == {"id", "telegram_id", "timezone", "active_mascot_code", "created_at"}
    assert columns.isdisjoint(forbidden_pii)


def test_telegram_id_is_a_unique_required_bigint() -> None:
    telegram_id = User.__table__.c.telegram_id

    assert isinstance(telegram_id.type, BigInteger)
    assert telegram_id.nullable is False
    assert telegram_id.unique is True


def test_timezone_has_safe_python_and_database_defaults() -> None:
    timezone = User.__table__.c.timezone

    assert isinstance(timezone.type, String)
    assert timezone.type.length == 64
    assert timezone.nullable is False
    assert timezone.default is not None
    assert timezone.default.arg == "UTC"
    assert timezone.server_default is not None
    assert str(timezone.server_default.arg) == "'UTC'"


def test_database_generates_uuid_and_timezone_aware_creation_time() -> None:
    user_id = User.__table__.c.id
    created_at = User.__table__.c.created_at

    assert isinstance(user_id.type, Uuid)
    assert user_id.nullable is False
    assert user_id.server_default is not None
    assert str(user_id.server_default.arg) == "gen_random_uuid()"

    assert isinstance(created_at.type, DateTime)
    assert created_at.type.timezone is True
    assert created_at.nullable is False
    assert created_at.server_default is not None
    assert str(created_at.server_default.arg) == "now()"
