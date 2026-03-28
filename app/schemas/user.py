from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MeResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    email: str | None = None
    apple_user_id: str = Field(serialization_alias="appleUserId")
    created_at: datetime = Field(serialization_alias="createdAt")
    last_sync_at: datetime | None = Field(serialization_alias="lastSyncAt", default=None)


class DeleteAccountRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    trigger: str = "self_service"
    app_version: str | None = Field(default=None, alias="appVersion")
    device_id: str | None = Field(default=None, alias="deviceId")
