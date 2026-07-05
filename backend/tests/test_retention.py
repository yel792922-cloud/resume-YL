"""Retention policy: caps raw uploads per user while preserving parsed data."""
from __future__ import annotations

import os

from app.core.db import SessionLocal
from app.models.document import Document
from app.storage.retention import enforce_retention


def test_retention_removes_old_raw_but_keeps_data(client, alice):
    headers = alice["headers"]
    user_id = alice["user"]["id"]

    # Create 3 documents for the user.
    ids = [client.post("/api/documents/seed", headers=headers).json()["id"] for _ in range(3)]

    db = SessionLocal()
    try:
        # Keep only the newest 1 raw file.
        removed = enforce_retention(db, user_id, keep=1)
        assert len(removed) == 2

        docs = {d.id: d for d in db.query(Document).filter(Document.user_id == user_id).all()}
        # The two oldest lost their raw file; the newest kept it.
        assert docs[ids[0]].raw_available is False and docs[ids[0]].storage_path is None
        assert docs[ids[2]].raw_available is True and docs[ids[2]].storage_path
    finally:
        db.close()

    # Structured data survives: facts + history still queryable for a trimmed doc.
    facts = client.get(f"/api/documents/{ids[0]}/facts", headers=headers).json()
    assert len(facts) > 10
    hist = client.get(f"/api/documents/{ids[0]}/history", headers=headers).json()
    assert hist and hist[0]["fact_count"] > 0
    # And its raw file is gone from disk.
    db = SessionLocal()
    try:
        d0 = db.get(Document, ids[0])
        assert d0.storage_path is None
    finally:
        db.close()


def test_delete_removes_raw_file(client, seeded):
    did, headers = seeded
    db = SessionLocal()
    try:
        path = db.get(Document, did).storage_path
    finally:
        db.close()
    assert path and os.path.exists(path)
    assert client.delete(f"/api/documents/{did}", headers=headers).status_code == 200
    assert not os.path.exists(path)
