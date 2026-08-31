import base64
from datetime import UTC, date, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.modules.praises.schemas import IV_BYTES, PraiseCreateRequest, PraiseEntry


def b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


def valid_payload() -> dict[str, str]:
    return {"body_ciphertext": b64(b"cipher-bytes"), "iv": b64(bytes(IV_BYTES))}


def test_valid_payload_exposes_decoded_bytes() -> None:
    request = PraiseCreateRequest(**valid_payload())

    assert request.ciphertext_bytes == b"cipher-bytes"
    assert request.iv_bytes == bytes(IV_BYTES)


def test_invalid_base64_ciphertext_is_rejected() -> None:
    payload = valid_payload()
    payload["body_ciphertext"] = "not base64!!!"

    with pytest.raises(ValidationError):
        PraiseCreateRequest(**payload)


def test_iv_must_be_twelve_bytes() -> None:
    payload = valid_payload()
    payload["iv"] = b64(bytes(8))

    with pytest.raises(ValidationError):
        PraiseCreateRequest(**payload)


def test_empty_ciphertext_is_rejected() -> None:
    payload = valid_payload()
    payload["body_ciphertext"] = b64(b"")

    with pytest.raises(ValidationError):
        PraiseCreateRequest(**payload)


def test_client_supplied_date_is_ignored() -> None:
    request = PraiseCreateRequest(**valid_payload(), local_date="2000-01-01")

    assert not hasattr(request, "local_date")


def test_entry_encodes_stored_bytes_as_base64() -> None:
    praise = SimpleNamespace(
        id=uuid4(),
        user_id=uuid4(),
        body_ciphertext=b"cipher-bytes",
        iv=bytes(IV_BYTES),
        local_date=date(2026, 9, 1),
        created_at=datetime(2026, 9, 1, 10, 0, tzinfo=UTC),
    )

    entry = PraiseEntry.from_praise(praise)

    assert base64.b64decode(entry.body_ciphertext) == b"cipher-bytes"
    assert base64.b64decode(entry.iv) == bytes(IV_BYTES)
    assert entry.id == praise.id
    assert entry.local_date == praise.local_date
    assert not hasattr(entry, "user_id")
