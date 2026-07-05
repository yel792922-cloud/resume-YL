"""Authentication flow: register, login, me, and rejection of bad credentials."""
from __future__ import annotations

from tests.conftest import register


def test_register_and_me(client):
    a = register(client, "new@example.com")
    me = client.get("/api/auth/me", headers=a["headers"]).json()
    assert me["email"] == "new@example.com"


def test_duplicate_email_rejected(client):
    register(client, "dup@example.com")
    res = client.post("/api/auth/register", json={"email": "dup@example.com", "password": "password123"})
    assert res.status_code == 409


def test_login_success_and_failure(client):
    register(client, "login@example.com", password="password123")
    ok = client.post("/api/auth/login", json={"email": "login@example.com", "password": "password123"})
    assert ok.status_code == 200 and ok.json()["access_token"]

    bad = client.post("/api/auth/login", json={"email": "login@example.com", "password": "wrong-password"})
    assert bad.status_code == 401


def test_unauthenticated_requests_rejected(client):
    assert client.get("/api/documents").status_code == 401
    assert client.get("/api/auth/me").status_code == 401
    assert client.post("/api/documents/seed").status_code == 401


def test_short_password_rejected(client):
    res = client.post("/api/auth/register", json={"email": "x@example.com", "password": "short"})
    assert res.status_code == 422
