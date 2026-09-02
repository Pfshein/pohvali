from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SessionRequest(BaseModel):
    timezone: str = Field(min_length=1, max_length=64)

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        try:
            return ZoneInfo(value).key
        except (ValueError, ZoneInfoNotFoundError):
            raise ValueError("timezone must be a known IANA timezone") from None


class UserProfile(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    timezone: str
    role: Literal["user", "admin"]
