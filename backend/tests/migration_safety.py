from collections.abc import Mapping

from sqlalchemy.engine import make_url


def require_test_database_url(environment: Mapping[str, str]) -> str:
    if environment.get("APP_ENV") != "test":
        raise ValueError("migration tests require APP_ENV=test")

    database_url = environment.get("DATABASE_URL")
    if not database_url:
        raise ValueError("migration tests require an explicit DATABASE_URL")

    database_name = make_url(database_url).database
    if database_name is None or not database_name.endswith("_test"):
        raise ValueError("migration test database name must end with _test")

    return database_url
