"""Public unsubscribe endpoint. No auth — protected by HMAC-signed token."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from standfast.core.dependencies import DbSession
from standfast.core.errors import AppError
from standfast.features.broadcasts import service

router = APIRouter()


_PAGE_STYLE = (
    "body{font-family:system-ui,sans-serif;max-width:480px;"
    "margin:80px auto;padding:0 16px;color:#111}"
)

_OK_PAGE = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Unsubscribed</title>
<style>{_PAGE_STYLE}</style>
</head><body>
<h1>You're unsubscribed</h1>
<p>You won't receive any more project-update emails from Standfast.
If this was a mistake, email us back and we'll add you again.</p>
</body></html>
"""

_BAD_PAGE = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Invalid link</title>
<style>{_PAGE_STYLE}</style>
</head><body>
<h1>This unsubscribe link is invalid or expired</h1>
<p>If you're trying to opt out, please reply to one of our emails
and we'll handle it manually.</p>
</body></html>
"""


@router.get("/{token}", response_class=HTMLResponse)
async def unsubscribe(token: str, db: DbSession) -> HTMLResponse:
    try:
        await service.record_unsubscribe(db, token)
    except AppError:
        return HTMLResponse(_BAD_PAGE, status_code=400)
    return HTMLResponse(_OK_PAGE)
