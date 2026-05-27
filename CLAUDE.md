# Standfast backend — agent notes

FastAPI service for the Standfast trading journal. Pairs with the Next.js frontend in `../standfast-web/`. See [README.md](README.md) for stack, setup, and layout.

## Hard rules

- **Routers in `api/v1/<feature>.py` stay thin.** No SQL, no business logic — only HTTP glue that calls a service function.
- **Business logic lives in `features/<feature>/service.py`.** Services must not import FastAPI; they're called from routers AND background tasks.
- **SQL lives in `features/<feature>/repository.py`.** No `select()` / `insert()` outside repositories.
- **Pydantic schemas (`schemas.py`) are the public contract.** Never return ORM models from a service.
- **Feature folder names match the frontend's `src/features/<name>/` exactly.** Use `rules_risk` (snake_case) for what the frontend calls `rules-risk`.
- **Migrations through Alembic only.** Don't `CREATE TABLE` via Supabase dashboard; the repo is the source of truth.
- **All I/O is async.** Async SQLAlchemy sessions, async route handlers, `httpx.AsyncClient` for outbound calls.

## Adding a new feature

1. Create `src/standfast/features/<name>/` with `models.py`, `schemas.py`, `repository.py`, `service.py`, `__init__.py`.
2. Create `src/standfast/api/v1/<name>.py` with the router and include it from [`api/v1/router.py`](src/standfast/api/v1/router.py).
3. Generate a migration: `uv run alembic revision --autogenerate -m "add <name> tables"`. Review the diff before committing.
4. Add a test under `tests/features/<name>/`.

## Auth

`Authorization: Bearer <supabase-jwt>` → verified by [`core/security.py`](src/standfast/core/security.py) → exposed as `CurrentUser` dependency (Supabase user_id + email + claims). HS256 only for now; RS256/JWKS is deferred.

## Commands

```powershell
uv sync                                                  # install deps
uv run uvicorn standfast.main:app --reload --port 8000   # dev server
uv run alembic revision --autogenerate -m "..."          # new migration
uv run alembic upgrade head                              # apply migrations
uv run pytest                                            # tests
uv run ruff check . && uv run mypy src                   # lint + typecheck
```
