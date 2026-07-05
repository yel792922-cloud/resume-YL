"""Shared test fixtures.

The whole suite runs against one throwaway SQLite database (configured before
the app is imported). Tests stay isolated from each other by using distinct
users — which also exercises the real multi-user code paths.
"""
from __future__ import annotations

import os
import tempfile
import uuid

# Configure a throwaway DB + data dir *before* importing the app.
_TMP = tempfile.mkdtemp(prefix="fra-tests-")
os.environ.setdefault("FRA_DATABASE_URL", f"sqlite:///{os.path.join(_TMP, 'test.db')}")
os.environ.setdefault("FRA_DATA_DIR", os.path.join(_TMP, "data"))
os.environ.setdefault("FRA_SECRET_KEY", "test-secret-key-that-is-long-enough-1234567890")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def register(client: TestClient, email: str | None = None, password: str = "password123") -> dict:
    """Register a user and return {headers, token, user, email}."""
    email = email or f"user-{uuid.uuid4().hex[:10]}@example.com"
    res = client.post("/api/auth/register", json={"email": email, "password": password})
    assert res.status_code == 201, res.text
    body = res.json()
    return {
        "headers": {"Authorization": f"Bearer {body['access_token']}"},
        "token": body["access_token"],
        "user": body["user"],
        "email": email,
    }


@pytest.fixture()
def alice(client):
    # Unique per test so the shared DB never sees a duplicate registration.
    return register(client)


@pytest.fixture()
def seeded(client, alice):
    """A sample document owned by a fresh user; returns (document_id, headers)."""
    doc = client.post("/api/documents/seed", headers=alice["headers"]).json()
    return doc["id"], alice["headers"]
