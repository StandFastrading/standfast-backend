# Backend operational notes

## RLS / security (as of 2026-06-09)

- **Live RLS issue is RESOLVED.** Supabase flagged `rls_disabled_in_public` on
  `user_profiles` and `alembic_version`; RLS is now enabled on every public
  table (verified directly against the DB).
- **RLS fix is codified** in Alembic: `c3f8a1d2b4e6_enable_rls_backend_tables`
  enables RLS on `user_profiles`, `email_unsubscribes`, and `alembic_version`,
  so the fix cannot silently regress when the chain is applied.

## Pending migration: `email_unsubscribes` (broadcasts feature)

- `7a3f2c91e0d4_create_email_unsubscribes` is **PENDING** (not applied to the
  live DB). The DB is currently at `5e660857fb5c`.
- It backs the **broadcasts** feature: `POST /api/v1/broadcasts` (admin-only)
  mass-emails all Supabase auth users via Resend; `GET /api/v1/unsubscribe/{token}`
  records opt-outs. Not used by any beta path.
- **DO NOT run broadcasts during beta** unless intentionally configured
  (`RESEND_API_KEY`, `RESEND_FROM_EMAIL`, `UNSUBSCRIBE_SECRET`) **and tested** —
  a broadcast emails every auth user, including beta testers' addresses.
- **Apply `alembic upgrade head` later** only when we're ready to bring the
  broadcast/unsubscribe feature online. Doing so creates `email_unsubscribes`
  and (via the chained RLS migration) secures it in the same upgrade.
