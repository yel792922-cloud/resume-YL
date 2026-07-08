"""Guest mode: temporary, isolated, resets on new session — and never a
durable account."""
from __future__ import annotations

from tests.conftest import register


def _guest(client):
    r = client.post("/api/auth/guest")
    assert r.status_code == 200, r.text
    body = r.json()
    return body["access_token"], {"Authorization": f"Bearer {body['access_token']}"}, body["user"]


def test_guest_entry_is_marked_and_usable(client):
    tok, headers, user = _guest(client)
    assert user["is_guest"] is True
    # /me reflects the guest identity
    me = client.get("/api/auth/me", headers=headers).json()
    assert me["is_guest"] is True


def test_guest_data_resets_on_next_guest_entry(client):
    # First guest seeds a document.
    _, h1, _ = _guest(client)
    did = client.post("/api/documents/seed", headers=h1).json()["id"]
    assert client.get(f"/api/documents/{did}", headers=h1).status_code == 200

    # Entering as a guest again starts fresh — previous guest data is gone.
    _, h2, _ = _guest(client)
    docs = client.get("/api/documents", headers=h2).json()
    assert docs == []


def test_guest_logout_wipes_workspace(client):
    _, h, _ = _guest(client)
    client.post("/api/documents/seed", headers=h)
    client.post("/api/auth/logout", headers=h)
    _, h2, _ = _guest(client)
    assert client.get("/api/documents", headers=h2).json() == []


def test_guest_never_creates_a_second_account(client):
    from app.core.db import SessionLocal
    from app.models.user import User

    for _ in range(3):
        _guest(client)
    with SessionLocal() as db:
        guests = db.query(User).filter(User.is_guest.is_(True)).count()
    assert guests == 1   # one shared workspace, not one per entry


def test_guest_and_registered_accounts_are_isolated(client):
    alice = register(client, "alice-iso@example.com")
    a_doc = client.post("/api/documents/seed", headers=alice["headers"]).json()["id"]

    _, gh, _ = _guest(client)
    # Guest cannot see Alice's document, and resetting guest never touches hers.
    assert client.get(f"/api/documents/{a_doc}", headers=gh).status_code == 404
    _guest(client)  # reset guest workspace
    assert client.get(f"/api/documents/{a_doc}", headers=alice["headers"]).status_code == 200


def test_guest_email_cannot_be_registered_or_logged_in(client):
    from app.auth.guest import GUEST_EMAIL

    assert client.post("/api/auth/register", json={"email": GUEST_EMAIL, "password": "password123"}).status_code == 400
    # Ensure a guest workspace exists, then confirm password login is refused.
    _guest(client)
    assert client.post("/api/auth/login", json={"email": GUEST_EMAIL, "password": "password123"}).status_code == 401
