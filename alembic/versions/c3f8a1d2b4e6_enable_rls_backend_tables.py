"""enable RLS on backend-owned public tables

Codifies the fix for Supabase's `rls_disabled_in_public` advisory. The
Alembic-managed tables in the public schema were flagged (or would be, once
created) as publicly accessible with RLS off. Enabling RLS with no policies
denies anon / authenticated clients; the backend connects as a BYPASSRLS role,
so its own access is unaffected. `enable row level security` is idempotent, so
this is a no-op for tables already secured manually.

Covers `email_unsubscribes` as well (created by the immediately-preceding
revision) so applying the chain never leaves a new public table unsecured.

Revision ID: c3f8a1d2b4e6
Revises: 7a3f2c91e0d4
Create Date: 2026-06-09 00:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "c3f8a1d2b4e6"
down_revision: str | None = "7a3f2c91e0d4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Backend-owned tables that must have RLS enabled (Supabase flags any public
# table without it). The backend reaches them via a BYPASSRLS connection.
_TABLES = ("user_profiles", "email_unsubscribes", "alembic_version")


def upgrade() -> None:
    for table in _TABLES:
        op.execute(f"alter table public.{table} enable row level security")


def downgrade() -> None:
    for table in _TABLES:
        op.execute(f"alter table public.{table} disable row level security")
