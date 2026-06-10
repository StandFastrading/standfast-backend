"""Pydantic DTOs for beta entry — the public contract the frontend speaks to."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

BetaPhase = Literal["phase_1", "phase_2"]


class BetaEntryRequest(BaseModel):
    email: str
    access_code: str

    @field_validator("email")
    @classmethod
    def _normalize_email(cls, v: str) -> str:
        return v.strip().lower()

    @field_validator("access_code")
    @classmethod
    def _strip_code(cls, v: str) -> str:
        return v.strip()


class BetaEntryResponse(BaseModel):
    """A minted session for the frontend to set client-side, plus context."""

    access_token: str
    refresh_token: str
    expires_in: int
    beta_phase: BetaPhase
    is_new: bool


# --- Admin DTOs (admin-gated tester management) ------------------------------


class BetaTesterRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    beta_phase: BetaPhase
    is_active: bool
    user_id: UUID | None
    last_seen_at: datetime | None
    created_at: datetime


class BetaTesterCreate(BaseModel):
    email: str
    beta_phase: BetaPhase
    is_active: bool = True

    @field_validator("email")
    @classmethod
    def _normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class BetaTesterUpdate(BaseModel):
    """PATCH payload — only provided fields are changed."""

    is_active: bool | None = None
    beta_phase: BetaPhase | None = None
