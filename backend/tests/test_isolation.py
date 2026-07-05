"""Cross-user isolation: a user can never reach another user's documents."""
from __future__ import annotations

from tests.conftest import register


def test_no_cross_user_access(client, seeded):
    did, alice_headers = seeded
    bob = register(client, "bob@example.com")
    bh = bob["headers"]

    # Bob's library is empty and he can't see Alice's document count.
    assert client.get("/api/documents", headers=bh).json() == []

    # Every document-scoped endpoint returns 404 for Bob (not 403 — no leak).
    assert client.get(f"/api/documents/{did}", headers=bh).status_code == 404
    assert client.get(f"/api/documents/{did}/facts", headers=bh).status_code == 404
    assert client.get(f"/api/documents/{did}/summary", headers=bh).status_code == 404
    assert client.get(f"/api/documents/{did}/pages/1", headers=bh).status_code == 404
    assert client.get(f"/api/documents/{did}/search", params={"q": "revenue"}, headers=bh).status_code == 404
    assert client.get(f"/api/documents/{did}/export.csv", headers=bh).status_code == 404
    assert client.get(f"/api/documents/{did}/history", headers=bh).status_code == 404
    assert client.get("/api/compare", params=[("document_ids", did)], headers=bh).status_code == 404

    # Bob cannot mutate Alice's document either.
    assert client.post(f"/api/documents/{did}/favorite", headers=bh).status_code == 404
    assert client.delete(f"/api/documents/{did}", headers=bh).status_code == 404

    # Alice still owns and can access it.
    assert client.get(f"/api/documents/{did}", headers=alice_headers).status_code == 200
