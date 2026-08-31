import base64
import binascii
from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

MAX_CIPHERTEXT_BYTES = 4096
IV_BYTES = 12
MAX_CALENDAR_SPAN_DAYS = 366


def _decode_base64(value: str) -> bytes:
    try:
        return base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError):
        raise ValueError("must be valid base64") from None


class _EncryptedPraiseBody(BaseModel):
    model_config = ConfigDict(extra="ignore")

    body_ciphertext: str
    iv: str

    @field_validator("body_ciphertext")
    @classmethod
    def _validate_ciphertext(cls, value: str) -> str:
        if len(_decode_base64(value)) == 0:
            raise ValueError("ciphertext must not be empty")
        return value

    @field_validator("iv")
    @classmethod
    def _validate_iv(cls, value: str) -> str:
        if len(_decode_base64(value)) != IV_BYTES:
            raise ValueError(f"iv must decode to {IV_BYTES} bytes")
        return value

    @property
    def ciphertext_bytes(self) -> bytes:
        return _decode_base64(self.body_ciphertext)

    @property
    def iv_bytes(self) -> bytes:
        return _decode_base64(self.iv)


class PraiseCreateRequest(_EncryptedPraiseBody):
    pass


class PraiseEditRequest(_EncryptedPraiseBody):
    sticker: str | None = Field(default=None, max_length=32)


class PraiseCreated(BaseModel):
    id: UUID
    local_date: date
    star_awarded: bool
    balance: int


class CalendarDay(BaseModel):
    local_date: date
    count: int


class PraiseEntry(BaseModel):
    id: UUID
    local_date: date
    created_at: datetime
    iv: str
    body_ciphertext: str

    @classmethod
    def from_praise(cls, praise: object) -> "PraiseEntry":
        return cls(
            id=praise.id,
            local_date=praise.local_date,
            created_at=praise.created_at,
            iv=base64.b64encode(praise.iv).decode(),
            body_ciphertext=base64.b64encode(praise.body_ciphertext).decode(),
        )
