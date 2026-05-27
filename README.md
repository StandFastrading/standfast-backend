# standfast-backend

FastAPI backend for **Standfast** — the trading journal that helps day traders maintain emotional control.

Pairs with the Next.js frontend in the sibling `standfast-web/` directory (collocated, separate git repo). Verifies Supabase JWTs on the way in; owns trade, journal, rules, and analytics data in Postgres.

## Stack

- **Python 3.13** managed by **uv**
- **FastAPI** + **uvicorn** (ASGI)
- **SQLAlchemy 2.0 async** + **asyncpg** for Postgres
- **Alembic** for schema migrations
- **pydantic-settings** for typed env loading
- **PyJWT** for verifying Supabase HS256 tokens
- **pytest** + **pytest-asyncio** for tests

## Getting started

```powershell
# 1. Install uv if you don't have it
winget install --id=astral-sh.uv

# 2. Install deps (creates .venv, syncs from uv.lock)
uv sync

# 3. Configure env
copy .env.example .env
# Fill in DATABASE_URL, SUPABASE_JWT_SECRET, SUPABASE_SERVICE_ROLE_KEY

# 4. Run migrations
uv run alembic upgrade head

# 5. Run the dev server
uv run uvicorn standfast.main:app --reload --port 8000
```

OpenAPI docs at <http://localhost:8000/docs>.

## Layout

```
src/standfast/
  main.py              FastAPI app factory + lifespan
  core/                config, database, JWT security, DI, errors, logging
  api/v1/              HTTP routers (one file per feature) — thin glue, no business logic
  features/            domain logic, one folder per frontend feature
    <feature>/
      models.py        SQLAlchemy ORM models
      schemas.py       Pydantic request/response DTOs
      repository.py    DB queries (no business logic)
      service.py       Business logic (no FastAPI/HTTP)
  integrations/        external services (Supabase admin, brokers, market data)
  tasks/               background jobs
alembic/               migration env + versions
tests/                 pytest suite, mirrors src/standfast/features/ tree
```

Feature folders mirror `standfast-web/src/features/` 1:1 — finding the counterpart is a one-rule operation.

## Conventions

1. **Routers stay thin.** `api/v1/<feature>.py` only handles HTTP — parsing, status codes, calling `service.<func>(...)`. No SQL, no business rules.
2. **Service layer owns business logic.** `service.py` is the only place where rules are enforced. It must be callable from a background task with no FastAPI in scope.
3. **Repository owns SQL.** All `select()` / `insert()` / `update()` lives in `repository.py`. Services compose repositories.
4. **Schemas are the contract.** `schemas.py` defines what the frontend sees. Never leak ORM models out of `service.py`.
5. **Migrations in code, not the Supabase dashboard.** All schema changes go through Alembic.
6. **Never log or return secrets.** Service-role key + JWT secret are server-only.

## Auth

Frontend sends the Supabase session JWT in the `Authorization: Bearer <token>` header. [`core/security.py`](src/standfast/core/security.py) verifies the HS256 signature with `SUPABASE_JWT_SECRET` and exposes the user via the `CurrentUser` dependency.

## Deferred / known-missing

- Real Supabase admin client (currently a stub in [`integrations/supabase.py`](src/standfast/integrations/supabase.py))
- Background task runner (folder exists; pick arq vs. celery when first job lands)
- RS256 / JWKS-based JWT verification (HS256 only for now)
- Broker integrations, market data feeds
