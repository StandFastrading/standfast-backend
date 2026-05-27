"""Supabase admin client placeholder.

Today we only verify JWTs from the frontend (see core/security.py). When we need
admin actions — sending password resets, deleting users, signed URLs for Storage —
add the client + helpers here. Use `httpx.AsyncClient` against the Supabase REST
API with `SUPABASE_SERVICE_ROLE_KEY` as the bearer token.
"""

from __future__ import annotations
