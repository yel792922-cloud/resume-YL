"""v4.1 adjustments: analysis mode, external forecast assumptions, xlsx export."""
from __future__ import annotations

import io

import pytest

openpyxl = pytest.importorskip("openpyxl")


# ---- #2 raw/clean analysis mode ----
def test_mode_param_accepted_and_echoed(client, seeded):
    did, h = seeded
    for m in ("raw", "clean"):
        fc = client.get(f"/api/documents/{did}/forecast?mode={m}", headers=h).json()
        assert fc["mode"] == m
        cmp = client.get(f"/api/compare?document_ids={did}&mode={m}", headers=h).json()
        assert cmp["mode"] == m
        a = client.post(f"/api/documents/{did}/ask?mode={m}", headers=h, json={"question": "Why did revenue increase?"})
        assert a.status_code == 200 and not a.json()["insufficient"]


def test_invalid_mode_rejected(client, seeded):
    did, h = seeded
    assert client.get(f"/api/documents/{did}/forecast?mode=bogus", headers=h).status_code == 422


def test_raw_mode_pool_is_superset_of_clean(client, seeded):
    did, h = seeded
    from app.analysis import document_facts
    from app.core.db import SessionLocal
    from app.models.document import Document

    db = SessionLocal()
    try:
        doc = db.get(Document, did)
        raw = document_facts(db, doc, "raw")
        clean = document_facts(db, doc, "clean")
        assert len(raw) >= len(clean)
    finally:
        db.close()


# ---- #3 external scenario assumptions ----
def test_forecast_external_assumptions(client, seeded):
    did, h = seeded
    fc = client.get(f"/api/documents/{did}/forecast", headers=h).json()
    assert fc["external_note"] and "assumption" in fc["external_note"].lower()
    scen = {sa["scenario"]: sa["external_factors"] for sa in fc["external_assumptions"]}
    assert {"base", "bull", "bear"} <= set(scen)
    # covers the external driver dimensions requested
    blob = " ".join(scen["bear"]).lower()
    for driver in ("market", "macro", "regulat", "competition", "fx", "cost", "sentiment"):
        assert driver in blob


# ---- #1 structured xlsx export ----
def test_xlsx_export_sheets_and_fields(client, seeded):
    did, h = seeded
    r = client.get(f"/api/documents/{did}/export.xlsx?mode=clean&question=How healthy is cash flow?", headers=h)
    assert r.status_code == 200
    assert "spreadsheetml.sheet" in r.headers["content-type"]

    wb = openpyxl.load_workbook(io.BytesIO(r.content))
    for s in ("Raw Facts", "Cleaned Facts", "Forecast", "Source Mapping", "Scenario Assumptions", "QA Evidence"):
        assert s in wb.sheetnames

    headers = [c.value for c in wb["Raw Facts"][1]]
    for col in ("company", "report_period", "metric", "value", "unit", "yoy_qoq", "source_page", "source_snippet", "cleaning_status", "confidence"):
        assert col in headers
    assert wb["Raw Facts"].max_row > 1  # has data rows


def test_xlsx_without_question_has_no_qa_sheet(client, seeded):
    did, h = seeded
    r = client.get(f"/api/documents/{did}/export.xlsx", headers=h)
    wb = openpyxl.load_workbook(io.BytesIO(r.content))
    assert "QA Evidence" not in wb.sheetnames


def test_xlsx_owner_scoped(client, seeded):
    from tests.conftest import register

    did, _ = seeded
    bob = register(client, "bob-xlsx@example.com")
    assert client.get(f"/api/documents/{did}/export.xlsx", headers=bob["headers"]).status_code == 404
