from sqlalchemy import CheckConstraint, Date, Integer, String

from app.models import StarBalance, StarLedgerEntry


def test_ledger_columns_are_append_only_shape() -> None:
    columns = set(StarLedgerEntry.__table__.columns.keys())

    assert columns == {"id", "user_id", "amount", "reason", "local_date", "created_at"}


def test_ledger_amount_and_reason_types() -> None:
    amount = StarLedgerEntry.__table__.c.amount
    reason = StarLedgerEntry.__table__.c.reason

    assert isinstance(amount.type, Integer)
    assert amount.nullable is False
    assert isinstance(reason.type, String)
    assert reason.nullable is False


def test_daily_star_has_a_partial_unique_index() -> None:
    index = next(
        index
        for index in StarLedgerEntry.__table__.indexes
        if index.name == "uq_star_ledger_daily_per_day"
    )

    assert index.unique is True
    assert tuple(column.name for column in index.columns) == ("user_id", "local_date")
    where = index.dialect_options["postgresql"]["where"]
    assert "daily" in str(where)


def test_ledger_local_date_is_nullable_date() -> None:
    local_date = StarLedgerEntry.__table__.c.local_date

    assert isinstance(local_date.type, Date)
    assert local_date.nullable is True


def test_balance_cannot_go_negative() -> None:
    checks = [
        constraint
        for constraint in StarBalance.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    ]

    assert any("balance >= 0" in str(check.sqltext) for check in checks)


def test_balance_defaults_to_zero_and_is_keyed_by_user() -> None:
    balance = StarBalance.__table__.c.balance
    user_id = StarBalance.__table__.c.user_id

    assert isinstance(balance.type, Integer)
    assert balance.nullable is False
    assert str(balance.server_default.arg) == "0"
    assert user_id.primary_key is True


def test_both_tables_cascade_on_user_delete() -> None:
    for table in (StarLedgerEntry, StarBalance):
        foreign_key = next(iter(table.__table__.c.user_id.foreign_keys))
        assert foreign_key.column.table.name == "users"
        assert foreign_key.ondelete == "CASCADE"
