"""Common FastAPI dependency aliases — import these in routers."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from .config import get_settings
from .database import get_db_session
from .security import CurrentUser, CurrentUserDep, get_current_user  # re-export

DbSession = Annotated[AsyncSession, Depends(get_db_session)]


async def require_admin(user: CurrentUserDep) -> CurrentUser:
    """Gate routes behind the ADMIN_EMAILS env allowlist."""
    settings = get_settings()
    allowlist = {e.lower() for e in settings.admin_emails}
    if not allowlist or not user.email or user.email.lower() not in allowlist:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="admin required")
    return user


AdminUserDep = Annotated[CurrentUser, Depends(require_admin)]

__all__ = ["AdminUserDep", "CurrentUserDep", "DbSession", "get_current_user"]
