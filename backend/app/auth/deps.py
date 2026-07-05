"""FastAPI dependencies for authentication and ownership."""
from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth.security import decode_token
from app.core.db import get_db
from app.models.user import User

# auto_error=False so we can raise a consistent 401 with a WWW-Authenticate hint.
_bearer = HTTPBearer(auto_error=False)

_UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or not credentials.credentials:
        raise _UNAUTHORIZED
    payload = decode_token(credentials.credentials)
    if not payload or "sub" not in payload:
        raise _UNAUTHORIZED
    try:
        user_id = int(payload["sub"])
    except (TypeError, ValueError):
        raise _UNAUTHORIZED
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise _UNAUTHORIZED
    return user
