"""ORM models for the beta-access domain.

These tables are owned and created by the web Supabase migration
(`standfast-web/supabase/migrations/20260606000003_beta_access_gating.sql`),
not by Alembic. The models here only map the existing tables for querying —
do not generate DDL for them.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.dialects.postgresql import ENUM as PgEnum
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from standfast.core.database import Base


def _beta_phase_enum() -> PgEnum:
    """Maps the existing Postgres `beta_phase` enum so parameters bind as the
    enum type (not VARCHAR). create_type=False: the web migration owns the DDL,
    so SQLAlchemy must never try to create or drop the type."""
    return PgEnum("phase_1", "phase_2", name="beta_phase", create_type=False)


class BetaTester(Base):
    """An approved beta tester. Preloaded by the operator; `user_id` is filled
    in by the backend on the tester's first successful entry."""

    __tablename__ = "beta_testers"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    email: Mapped[str] = mapped_column(String)  # citext in Postgres
    beta_phase: Mapped[str] = mapped_column(_beta_phase_enum())
    is_active: Mapped[bool] = mapped_column(Boolean)
    user_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class BetaAccessCode(Base):
    """Canonical phase -> access-code mapping (one active code per phase)."""

    __tablename__ = "beta_access_codes"

    beta_phase: Mapped[str] = mapped_column(_beta_phase_enum(), primary_key=True)
    code: Mapped[str] = mapped_column(String)
    is_active: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
