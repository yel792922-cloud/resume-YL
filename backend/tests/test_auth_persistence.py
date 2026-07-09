"""Auth persistence + production config stability.

Guards the fixes for the "accounts/login disappear" problem: registrations are
written to the real database (survive a fresh session), token login survives a
'refresh', and production never silently runs on ephemeral SQLite.
"""
from __future__ import annotations

import pytest

from tests.conftest import register


def test_registration_is_written_to_the_database(client):
    from app.core.db import SessionLocal
    from app.models.user import User

    reg = register(client, "durable@example.com")
    # A brand-new DB session (simulating a later request / restart) sees the row.
    with SessionLocal() as db:
        row = db.query(User).filter(User.email == "durable@example.com").first()
    assert row is not None
    assert row.id == reg["user"]["id"]
    assert row.is_guest is False


def test_login_state_survives_refresh(client):
    reg = register(client, "refresh@example.com")
    # Simulate a page refresh: the client re-validates the stored token via /me.
    me = client.get("/api/auth/me", headers=reg["headers"]).json()
    assert me["email"] == "refresh@example.com"
    # And logging in again returns a working token for the same durable user.
    res = client.post("/api/auth/login", json={"email": "refresh@example.com", "password": "password123"}).json()
    assert res["user"]["id"] == reg["user"]["id"]


def test_duplicate_registration_rejected(client):
    register(client, "dup-persist@example.com")
    r = client.post("/api/auth/register", json={"email": "dup-persist@example.com", "password": "password123"})
    assert r.status_code == 409


def test_user_lookup_is_database_backed(client):
    reg = register(client, "lookup@example.com")
    # Deactivating the row in the DB immediately invalidates the token (proves
    # the dependency resolves the live DB row, not a cached identity).
    from app.core.db import SessionLocal
    from app.models.user import User

    with SessionLocal() as db:
        u = db.query(User).filter(User.email == "lookup@example.com").first()
        u.is_active = False
        db.commit()
    assert client.get("/api/auth/me", headers=reg["headers"]).status_code == 401


# ---------------------------- production config ----------------------------

def _settings(**kw):
    from app.core.config import Settings
    return Settings(**kw)


def test_durable_db_required_but_sqlite_fails_fast():
    from app.main import _check_production_config

    s = _settings(require_durable_db=True, database_url="sqlite:///./x.db",
                  secret_key="a-long-enough-real-secret-key-000000000000")
    with pytest.raises(RuntimeError, match="durable database"):
        _check_production_config(s)


def test_dev_secret_with_durable_db_fails_fast():
    from app.core.config import DEFAULT_DEV_SECRET
    from app.main import _check_production_config

    s = _settings(require_durable_db=True,
                  database_url="postgresql+psycopg://u:p@host/db",
                  secret_key=DEFAULT_DEV_SECRET)
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        _check_production_config(s)


def test_local_sqlite_dev_is_allowed():
    from app.core.config import DEFAULT_DEV_SECRET
    from app.main import _check_production_config

    s = _settings(require_durable_db=False, database_url="sqlite:///./x.db",
                  secret_key=DEFAULT_DEV_SECRET)
    _check_production_config(s)  # should not raise
    assert s.db_backend == "sqlite"


def test_db_backend_reports_postgres_without_credentials():
    s = _settings(database_url="postgresql+psycopg://user:secret@host:5432/db")
    assert s.db_backend == "postgresql"          # backend name, no +driver, no creds
    assert "secret" not in s.db_backend
