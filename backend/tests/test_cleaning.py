"""Data-cleaning layer: dedup, noise filtering, unit normalization, traceability."""
from __future__ import annotations

from app.cleaning import clean_facts
from app.models.fact import ExtractedFact, FactCategory


def _numeric(id_, concept, value, unit="亿元", conf=0.9, page=1, snippet=None):
    return ExtractedFact(
        id=id_,
        document_id="doc1",
        category=FactCategory.INCOME_STATEMENT,
        concept_id=concept,
        metric_name=concept.title(),
        metric_value=value,
        unit=unit,
        confidence_score=conf,
        source_page_number=page,
        source_text_snippet=snippet or f"{concept} {value}",
    )


def _section(id_, category, snippet, conf=0.5, page=2):
    return ExtractedFact(
        id=id_,
        document_id="doc1",
        category=category,
        concept_id=None,
        metric_name="Risk Factor",
        metric_value=None,
        value_text=snippet,
        confidence_score=conf,
        source_page_number=page,
        source_text_snippet=snippet,
    )


def test_removes_boilerplate_and_page_numbers_but_keeps_numeric():
    facts = [
        _numeric(1, "revenue", 6096.9),
        _section(2, FactCategory.RISK, "第 12 页"),                 # page number
        _section(3, FactCategory.MANAGEMENT, "免责声明：本报告不构成投资建议"),  # disclaimer
        _section(4, FactCategory.RISK, "应收账款增长较快，存在回款风险。"),      # real risk -> keep
    ]
    result = clean_facts(facts)
    kept_ids = {f.id for f in result.retained}
    assert 1 in kept_ids                      # numeric fact always kept
    assert 4 in kept_ids                      # genuine risk kept
    assert 2 not in kept_ids and 3 not in kept_ids
    reasons = {a.fact_id: a.reason for a in result.audit if a.action == "removed"}
    assert 2 in reasons and 3 in reasons      # audit records why


def test_deduplicates_identical_numeric_facts():
    facts = [
        _numeric(1, "revenue", 6096.9, conf=0.9, page=1),
        _numeric(2, "revenue", 6096.9, conf=0.6, page=5),   # duplicate, lower confidence
    ]
    result = clean_facts(facts)
    assert len(result.retained) == 1
    assert result.retained[0].id == 1                        # higher-confidence kept
    assert any(a.action == "deduped" and a.fact_id == 2 for a in result.audit)


def test_normalizes_units_without_mutating_source():
    f = _numeric(1, "revenue", 6096.9, unit="人民币（亿元）")
    result = clean_facts([f])
    assert result.unit_for(f) == "亿元"                      # normalized for output
    assert f.unit == "人民币（亿元）"                          # ORM object untouched
    assert any(a.action == "normalized" for a in result.audit)


def test_traceability_preserved_on_retained():
    facts = [_numeric(1, "revenue", 6096.9, page=3)]
    result = clean_facts(facts)
    assert result.retained[0].source_page_number == 3


def test_api_cleaned_endpoint(client, seeded):
    did, headers = seeded
    res = client.get(f"/api/documents/{did}/cleaned", headers=headers).json()
    assert res["stats"]["retained"] > 10
    assert all(f["source"]["page_number"] for f in res["retained"])


def test_cleaned_endpoint_owner_scoped(client, seeded):
    from tests.conftest import register

    did, _ = seeded
    bob = register(client, "bob-clean@example.com")
    assert client.get(f"/api/documents/{did}/cleaned", headers=bob["headers"]).status_code == 404
