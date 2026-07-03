"""End-to-end smoke test over the built-in sample report.

Exercises the whole pipeline: seed → parse → extract (with traceability) →
facts / summary / search / compare / export.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def seeded(client) -> str:
    return client.post("/api/documents/seed").json()["id"]


def test_seed_extracts_core_metrics(client, seeded):
    facts = client.get(f"/api/documents/{seeded}/facts").json()
    by_concept = {f["concept_id"]: f for f in facts if f["concept_id"]}
    for concept in ("revenue", "net_profit", "gross_margin", "operating_cash_flow", "total_assets"):
        assert concept in by_concept, f"missing {concept}"

    revenue = by_concept["revenue"]
    assert revenue["metric_value"] == pytest.approx(6096.9)
    # Every fact must be traceable to a source page.
    assert all(f["source"]["page_number"] for f in facts)
    # Table-sourced facts carry a cell reference + bbox.
    assert revenue["source"]["table_cell"] is not None
    assert revenue["source"]["bbox"] is not None


def test_bilingual_search(client, seeded):
    # Searching in Chinese finds the English-named metric via the concept layer.
    res = client.get(f"/api/documents/{seeded}/search", params={"q": "毛利率"}).json()
    assert res["total"] > 0
    assert any(h["kind"] == "fact" and h["bbox"] for h in res["hits"])


def test_summary_is_evidence_linked(client, seeded):
    summ = client.get(f"/api/documents/{seeded}/summary").json()
    assert summ["headline_metrics"]
    assert all(h["source"] for h in summ["highlights"])
    assert summ["risks"]


def test_export_roundtrip(client, seeded):
    csv_text = client.get(f"/api/documents/{seeded}/export.csv").text
    assert "source_page_number" in csv_text.splitlines()[0]
    assert len(client.get(f"/api/documents/{seeded}/export.json").json()) > 10


def test_compare_two_documents(client, seeded):
    other = client.post("/api/documents/seed").json()["id"]
    comp = client.get(
        "/api/compare",
        params=[("document_ids", seeded), ("document_ids", other), ("dimension", "period")],
    ).json()
    assert len(comp["columns"]) == 2
    assert any(r["concept_id"] == "revenue" for r in comp["rows"])
