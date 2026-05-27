"""ORM models for the account domain."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from standfast.core.database import Base


class UserProfile(Base):
    """Per-user data that augments Supabase Auth — anything we want queryable in our own Postgres.

    Keyed by the Supabase user UUID (`sub` claim from the JWT). One row per user, created on first
    authenticated request via `service.get_or_create_profile`.
    """

    __tablename__ = "user_profiles"

    user_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    display_name: Mapped[str | None] = mapped_column(String(120))
    timezone: Mapped[str | None] = mapped_column(String(64))
    primary_market: Mapped[str | None] = mapped_column(String(32))  # forex|futures|crypto|options
    onboarding_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
