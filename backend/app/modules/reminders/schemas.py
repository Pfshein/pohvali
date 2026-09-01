from pydantic import BaseModel

from app.modules.reminders.service import ReminderSettings


class ReminderSettingsResponse(BaseModel):
    enabled: bool
    dm_available: bool

    @classmethod
    def from_settings(cls, settings: ReminderSettings) -> "ReminderSettingsResponse":
        return cls(enabled=settings.enabled, dm_available=settings.dm_available)


class ReminderUpdateRequest(BaseModel):
    enabled: bool
