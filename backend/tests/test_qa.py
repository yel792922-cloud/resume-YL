"""Evidence-based Q&A: intent routing, grounded answers, citations, ownership."""
from __future__ import annotations

from app.qa.intent import (
    CASH_HEALTH,
    GENERAL,
    METRIC_LOOKUP,
    PERIOD_CHANGE,
    RISKS,
    WHY_CHANGE,
    classify,
)


# ---- Intent classification (pure) ----
def test_intent_routing():
    assert classify("Why did revenue increase?").intent == WHY_CHANGE
    assert classify("为什么营业收入增长？").intent == WHY_CHANGE
    assert classify("What are the main risks?").intent == RISKS
    assert classify("How healthy is cash flow?").intent == CASH_HEALTH
    assert classify("What changed versus the previous period?").intent == PERIOD_CHANGE
    assert classify("What was net profit?").intent == METRIC_LOOKUP
    assert classify("Tell me a joke").intent == GENERAL


def test_intent_detects_concept():
    qi = classify("Why did gross margin fall?")
    assert "gross_margin" in qi.concepts


# ---- Answer composition (via API, on the sample report) ----
def _ask(client, did, headers, q):
    return client.post(f"/api/documents/{did}/ask", headers=headers, json={"question": q}).json()


def test_why_change_is_grounded_with_evidence(client, seeded):
    did, headers = seeded
    r = _ask(client, did, headers, "Why did revenue increase?")
    assert r["intent"] == "why_change"
    assert not r["insufficient"]
    assert "8.4%" in r["answer"] or "8.3%" in r["answer"]     # observed delta from the report
    # Every evidence item is source-traceable (has a page to jump to).
    assert r["evidence"] and all(e["source"]["page_number"] for e in r["evidence"])


def test_risks_lists_report_risks(client, seeded):
    did, headers = seeded
    r = _ask(client, did, headers, "What are the main risks?")
    assert r["intent"] == "risks"
    assert len(r["evidence"]) >= 1
    assert all(e["source"]["page_number"] for e in r["evidence"])


def test_cash_health_uses_cash_metrics(client, seeded):
    did, headers = seeded
    r = _ask(client, did, headers, "How healthy is cash flow?")
    assert r["intent"] == "cash_health"
    assert "Cash Flow" in r["answer"] or "现金流" in r["answer"]
    assert not r["insufficient"]


def test_period_change_reports_deltas(client, seeded):
    did, headers = seeded
    r = _ask(client, did, headers, "What changed versus the previous period?")
    assert r["intent"] == "period_change"
    assert "%" in r["answer"] and r["evidence"]


def test_unanswerable_is_conservative(client, seeded):
    did, headers = seeded
    r = _ask(client, did, headers, "What is the CEO's favorite color?")
    assert r["insufficient"] is True
    assert r["confidence"] == "low"
    assert r["evidence"] == []
    assert r["note"]                                         # conservative caveat present


def test_empty_question_rejected(client, seeded):
    did, headers = seeded
    # Truly empty is rejected by validation…
    assert client.post(f"/api/documents/{did}/ask", headers=headers, json={"question": ""}).status_code == 422
    # …and a blank/whitespace question degrades gracefully (no crash), not a 500.
    r = client.post(f"/api/documents/{did}/ask", headers=headers, json={"question": "   "})
    assert r.status_code == 200 and r.json()["insufficient"] is True


def test_ask_owner_scoped(client, seeded):
    from tests.conftest import register

    did, _ = seeded
    bob = register(client, "bob-qa@example.com")
    r = client.post(f"/api/documents/{did}/ask", headers=bob["headers"], json={"question": "revenue?"})
    assert r.status_code == 404
