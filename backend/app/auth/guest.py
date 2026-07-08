"""Guest mode — a temporary, non-persistent access path.

A guest is NOT a real account. Instead of minting a durable user row per guest
(which would pollute the accounts table), all guests share one reserved
*workspace* row whose data is wiped on every guest entry and logout. So:

* no per-guest durable account is ever created;
* returning as a guest always starts a fresh, empty session (previous guest
  documents/history are gone);
* the workspace can never be logged into with a password and is excluded from
  the registered-account flows, keeping guest and real accounts isolated.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.user import User

# Sentinel identity for the shared guest workspace. The email is unusable for
# real registration (blocked in the register route) and login (unusable hash).
GUEST_EMAIL = "guest@local.guest"
_UNUSABLE_HASH = "!"  # never matches bcrypt.checkpw → password login impossible


def get_or_create_guest_workspace(db: Session) -> User:
    user = db.query(User).filter(User.is_guest.is_(True)).first()
    if user is None:
        user = User(email=GUEST_EMAIL, password_hash=_UNUSABLE_HASH, is_guest=True)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def reset_guest_workspace(db: Session, user: User) -> None:
    """Drop everything the guest workspace owns, so the next session is fresh.

    Deleting the documents cascades to their facts/pages/snapshots; the reserved
    workspace row itself is kept (it is a fixture, not a per-guest account).
    """
    docs = db.query(Document).filter(Document.user_id == user.id).all()
    for d in docs:
        db.delete(d)
    if docs:
        db.commit()


def enter_guest(db: Session) -> User:
    """Begin a fresh guest session: reset the workspace and return it."""
    user = get_or_create_guest_workspace(db)
    reset_guest_workspace(db, user)
    return user
