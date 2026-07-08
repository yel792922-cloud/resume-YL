"""Auth routes: register, login, current user, logout."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.auth.guest import GUEST_EMAIL, enter_guest, reset_guest_workspace
from app.auth.security import create_access_token, hash_password, verify_password
from app.core.db import get_db
from app.models.schemas import LoginRequest, RegisterRequest, TokenOut, UserOut
from app.models.user import User

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _issue_token(user: User, guest: bool = False) -> TokenOut:
    token = create_access_token(user.id, guest=guest)
    return TokenOut(access_token=token, user=UserOut.model_validate(user))


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    email = body.email.lower().strip()
    if email == GUEST_EMAIL:
        raise HTTPException(status_code=400, detail="This email is reserved")
    if db.query(User).filter(User.email == email).first() is not None:
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    user = User(email=email, password_hash=hash_password(body.password), is_guest=False)
    db.add(user)
    db.commit()
    db.refresh(user)
    return _issue_token(user)


@router.post("/login", response_model=TokenOut)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    email = body.email.lower().strip()
    user = db.query(User).filter(User.email == email).first()
    # A guest workspace is never a real login target, even if its email is guessed.
    if user is None or user.is_guest or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")
    return _issue_token(user)


@router.post("/guest", response_model=TokenOut)
def guest(db: Session = Depends(get_db)):
    """Enter a temporary guest session. Resets any prior guest data first, so a
    returning guest always starts fresh; no durable account is created."""
    user = enter_guest(db)
    return _issue_token(user, guest=True)


@router.get("/me", response_model=UserOut)
def me(current: User = Depends(get_current_user)):
    return UserOut.model_validate(current)


@router.post("/logout")
def logout(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Stateless JWT: the client discards the token. For a guest we also wipe the
    # workspace so nothing lingers after they leave.
    if current.is_guest:
        reset_guest_workspace(db, current)
    return {"status": "ok"}
