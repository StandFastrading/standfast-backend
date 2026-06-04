"""ORM models for the broadcasts domain."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from standfast.core.database import Base


class EmailUnsubscribe(Base):
    """One row per Supabase user who opted out of project-update emails.

    Keyed by Supabase user UUID. Email is captured at opt-out time as a record
    of what address the unsubscribe link was issued for, even if the user later
    changes their primary email in Supabase.
    """

    __tablename__ = "email_unsubscribes"

    user_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    unsubscribed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
