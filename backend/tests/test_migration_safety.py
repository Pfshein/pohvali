import pytest

from tests.migration_safety import require_test_database_url


@pytest.mark.parametrize(
    ("environment", "message"),
    [
        ({}, "APP_ENV=test"),
        (
            {
                "APP_ENV": "development",
                "DATABASE_URL": "postgresql+asyncpg://u:p@postgres/app_test",
            },
            "APP_ENV=test",
        ),
        ({"APP_ENV": "test"}, "DATABASE_URL"),
        (
            {
                "APP_ENV": "test",
                "DATABASE_URL": "postgresql+asyncpg://u:p@postgres/pohvala",
            },
            "_test",
        ),
    ],
)
def test_database_guard_rejects_unsafe_targets(
    environment: dict[str, str],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        require_test_database_url(environment)


def test_database_guard_accepts_an_explicit_test_database() -> None:
    database_url = "postgresql+asyncpg://u:p@postgres/pohvala_test"

    assert require_test_database_url(
        {"APP_ENV": "test", "DATABASE_URL": database_url}
    ) == database_url
