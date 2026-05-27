"""Pydantic DTOs — the public contract the frontend speaks to."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

PrimaryMarket = Literal["forex", "futures", "crypto", "options"]


class UserProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    display_name: str | None
    timezone: str | None
    primary_market: PrimaryMarket | None
    onboarding_completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class UserProfileUpdate(BaseModel):
    """PATCH payload — all fields optional, only provided fields are updated."""

    display_name: str | None = Field(default=None, max_length=120)
    timezone: str | None = Field(default=None, max_length=64)
    primary_market: PrimaryMarket | None = None
