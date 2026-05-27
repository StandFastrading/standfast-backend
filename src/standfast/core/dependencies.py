"""Common FastAPI dependency aliases — import these in routers."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_db_session
from .security import CurrentUserDep  # re-export for convenience

DbSession = Annotated[AsyncSession, Depends(get_db_session)]

__all__ = ["CurrentUserDep", "DbSession"]
