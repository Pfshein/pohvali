from sqlalchemy import Date, DateTime, LargeBinary, Uuid

from app.models import Praise  # aggregator import keeps the users FK target in metadata


def test_praise_persists_only_ciphertext_and_never_plaintext() -> None:
    columns = set(Praise.__table__.columns.keys())

    assert columns == {
        "id",
        "user_id",
        "body_ciphertext",
        "iv",
        "local_date",
        "created_at",
        "updated_at",
    }
    assert columns.isdisjoint({"body", "text", "plaintext", "body_plaintext"})


def test_ciphertext_and_iv_are_required_opaque_bytes() -> None:
    body = Praise.__table__.c.body_ciphertext
    iv = Praise.__table__.c.iv

    assert isinstance(body.type, LargeBinary)
    assert body.nullable is False
    assert isinstance(iv.type, LargeBinary)
    assert iv.nullable is False


def test_local_date_is_server_owned_required_date() -> None:
    local_date = Praise.__table__.c.local_date

    assert isinstance(local_date.type, Date)
    assert local_date.nullable is False
    assert local_date.default is None
    assert local_date.server_default is None


def test_user_id_is_a_required_cascade_foreign_key() -> None:
    user_id = Praise.__table__.c.user_id

    assert isinstance(user_id.type, Uuid)
    assert user_id.nullable is False
    foreign_key = next(iter(user_id.foreign_keys))
    assert foreign_key.column.table.name == "users"
    assert foreign_key.ondelete == "CASCADE"


def test_timestamps_are_timezone_aware_with_now_defaults() -> None:
    created_at = Praise.__table__.c.created_at
    updated_at = Praise.__table__.c.updated_at

    for column in (created_at, updated_at):
        assert isinstance(column.type, DateTime)
        assert column.type.timezone is True
        assert column.nullable is False
        assert str(column.server_default.arg) == "now()"


def test_calendar_index_covers_user_and_local_date() -> None:
    index_columns = {
        tuple(column.name for column in index.columns) for index in Praise.__table__.indexes
    }

    assert ("user_id", "local_date") in index_columns


def test_stats_index_covers_praise_creation_time() -> None:
    index_columns = {
        tuple(column.name for column in index.columns) for index in Praise.__table__.indexes
    }
    assert ("created_at",) in index_columns
