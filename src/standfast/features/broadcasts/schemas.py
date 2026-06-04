"""Pydantic DTOs — the public contract for the broadcasts API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class BroadcastRequest(BaseModel):
    """Payload for POST /v1/broadcasts. Caller supplies finished HTML."""

    subject: str = Field(min_length=1, max_length=200)
    html: str = Field(min_length=1)
    text: str | None = None


class BroadcastResult(BaseModel):
    sent: int
    failed: int
    unsubscribed_skipped: int
    no_email_skipped: int
