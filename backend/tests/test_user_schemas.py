from types import SimpleNamespace
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.modules.users.schemas import SessionRequest, UserProfile


@pytest.mark.parametrize("timezone", ["UTC", "Europe/Moscow"])
def test_session_request_accepts_known_iana_timezone(timezone: str) -> None:
    request = SessionRequest(timezone=timezone)

    assert request.timezone == timezone


@pytest.mark.parametrize(
    "timezone",
    ["Mars/Olympus", "../../etc/passwd", "", "A" * 65],
)
def test_session_request_rejects_non_iana_timezone(timezone: str) -> None:
    with pytest.raises(ValidationError):
        SessionRequest(timezone=timezone)


def test_user_profile_reads_only_public_orm_attributes() -> None:
    user = SimpleNamespace(
        id=UUID("0ecaf26f-ee72-4f06-ae79-41198dd1ac6d"),
        telegram_id=991_001,
        timezone="UTC",
        role="user",
        username="must-not-be-returned",
    )

    profile = UserProfile.model_validate(user)

    assert profile.model_dump(mode="json") == {
        "id": "0ecaf26f-ee72-4f06-ae79-41198dd1ac6d",
        "timezone": "UTC",
        "role": "user",
    }
