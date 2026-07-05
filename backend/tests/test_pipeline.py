"""End-to-end pipeline test over the built-in sample report (authenticated).

Exercises: seed → parse → extract (with traceability) → facts / summary /
search / compare / export — now scoped to an authenticated user.
"""
from __future__ import annotations

import pytest


def test_seed_extracts_core_metrics(client, seeded):
    did, headers = seeded
    facts = client.get(f"/api/documents/{did}/facts", headers=headers).json()
    by_concept = {f["concept_id"]: f for f in facts if f["concept_id"]}
    for concept in ("revenue", "net_profit", "gross_margin", "operating_cash_flow", "total_assets"):
        assert concept in by_concept, f"missing {concept}"

    revenue = by_concept["revenue"]
    assert revenue["metric_value"] == pytest.approx(6096.9)
    assert all(f["source"]["page_number"] for f in facts)
    assert revenue["source"]["table_cell"] is not None
    assert revenue["source"]["bbox"] is not None


def test_bilingual_search(client, seeded):
    did, headers = seeded
    res = client.get(f"/api/documents/{did}/search", params={"q": "毛利率"}, headers=headers).json()
    assert res["total"] > 0
    assert any(h["kind"] == "fact" and h["bbox"] for h in res["hits"])


def test_summary_is_evidence_linked(client, seeded):
    did, headers = seeded
    summ = client.get(f"/api/documents/{did}/summary", headers=headers).json()
    assert summ["headline_metrics"]
    assert all(h["source"] for h in summ["highlights"])
    assert summ["risks"]


def test_export_roundtrip(client, seeded):
    did, headers = seeded
    csv_text = client.get(f"/api/documents/{did}/export.csv", headers=headers).text
    assert "source_page_number" in csv_text.splitlines()[0]
    assert len(client.get(f"/api/documents/{did}/export.json", headers=headers).json()) > 10


def test_compare_two_documents(client, seeded):
    did, headers = seeded
    other = client.post("/api/documents/seed", headers=headers).json()["id"]
    comp = client.get(
        "/api/compare",
        params=[("document_ids", did), ("document_ids", other), ("dimension", "period")],
        headers=headers,
    ).json()
    assert len(comp["columns"]) == 2
    assert any(r["concept_id"] == "revenue" for r in comp["rows"])


def test_history_snapshot_created(client, seeded):
    did, headers = seeded
    hist = client.get(f"/api/documents/{did}/history", headers=headers).json()
    assert len(hist) == 1 and hist[0]["version"] == 1
    detail = client.get(f"/api/documents/{did}/history/1", headers=headers).json()
    assert detail["fact_count"] == len(detail["facts"]) > 0
    assert detail["summary"]["headline_metrics"]
