import hashlib
import hmac
import json
from datetime import UTC, datetime
from typing import Annotated
from urllib.parse import urlencode

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import get_telegram_identity
from app.core.config import Settings, get_settings
from app.security.telegram import TelegramIdentity

BOT_TOKEN = "dev-token"


def signed_init_data(*, telegram_id: int = 42) -> str:
    values = {
        "auth_date": str(int(datetime.now(UTC).timestamp())),
        "query_id": "AAHdF6IQAAAAAN0XohDhrOrc",
        "user": json.dumps(
            {
                "id": telegram_id,
                "first_name": "Must not leave the request",
                "username": "private",
            },
            separators=(",", ":"),
        ),
    }
    data_check_string = "\n".join(f"{key}={values[key]}" for key in sorted(values))
    secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    values["hash"] = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256,
    ).hexdigest()
    return urlencode(values)


def auth_test_client() -> TestClient:
    application = FastAPI()
    application.dependency_overrides[get_settings] = lambda: Settings(bot_token=BOT_TOKEN)

    @application.get("/identity")
    def identity(
        telegram_identity: Annotated[TelegramIdentity, Depends(get_telegram_identity)],
    ) -> dict[str, int]:
        return {"telegram_id": telegram_identity.telegram_id}

    return TestClient(application)


def test_valid_tma_header_returns_minimal_identity() -> None:
    response = auth_test_client().get(
        "/identity",
        headers={"Authorization": f"tma {signed_init_data(telegram_id=73)}"},
    )

    assert response.status_code == 200
    assert response.json() == {"telegram_id": 73}


def test_missing_authorization_is_rejected_without_echoing_credentials() -> None:
    response = auth_test_client().get("/identity")

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid Telegram authorization"}
    assert response.headers["www-authenticate"] == "tma"


def test_wrong_authorization_scheme_is_rejected() -> None:
    init_data = signed_init_data()

    response = auth_test_client().get(
        "/identity",
        headers={"Authorization": f"Bearer {init_data}"},
    )

    assert response.status_code == 401
    assert init_data not in response.text


def test_tampered_init_data_is_rejected_without_echoing_credentials() -> None:
    init_data = signed_init_data().replace("%22id%22%3A42", "%22id%22%3A99")

    response = auth_test_client().get(
        "/identity",
        headers={"Authorization": f"tma {init_data}"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid Telegram authorization"}
    assert init_data not in response.text
