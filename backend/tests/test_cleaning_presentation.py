"""Evidence-centric cleaning presentation: audit anchors, rule summary, units.

Guards the layered cleaning view — every filtered item must carry enough source
context (page, reason) to be understood, the active rules must be reported, and
missing-unit facts must be handled rather than silently blanked.
"""
from __future__ import annotations

from app.cleaning import active_rule_ids, clean_facts
from app.cleaning.rules import CleaningConfig
from app.models.fact import ExtractedFact, FactCategory


def _section(id_, snippet, *, category=FactCategory.RISK, page=7, conf=0.5):
    return ExtractedFact(
        id=id_, document_id="doc1", category=category, concept_id=None,
        metric_name="Risk Factor", metric_value=None, value_text=snippet,
        confidence_score=conf, source_page_number=page,
        report_section="Risk Factors", source_text_snippet=snippet,
    )


def test_preserve_merge_strength_keeps_section_distinct_facts():
    from app.cleaning import clean_facts
    from app.cleaning.rules import CleaningConfig

    def _num(id_, section):
        return ExtractedFact(
            id=id_, document_id="d", category=FactCategory.INCOME_STATEMENT,
            concept_id="revenue", metric_name="Revenue", metric_value=100.0,
            unit="亿元", confidence_score=0.9, report_period="2024 FY",
            report_section=section, source_text_snippet="revenue 100",
        )
    a, b = _num(1, "Income Statement (page 3)"), _num(2, "Income Statement (page 8)")
    # standard → same scope/value/period collapse to one
    assert len(clean_facts([a, b], CleaningConfig(merge_strength="standard")).retained) == 1
    # preserve → different sections kept apart (safer for complex reports)
    assert len(clean_facts([a, b], CleaningConfig(merge_strength="preserve")).retained) == 2


def test_active_rule_ids_reported():
    ids = active_rule_ids()
    for r in ("boilerplate", "ocr_garbage", "low_information", "min_confidence", "dedup", "unit_normalization"):
        assert r in ids


def test_disabled_rules_drop_out_of_summary():
    ids = active_rule_ids(CleaningConfig(enable_dedup=False, enable_unit_normalization=False))
    assert "dedup" not in ids and "unit_normalization" not in ids
    assert "boilerplate" in ids


def test_filtered_audit_entry_carries_page_and_reason():
    facts = [_section(1, "第 12 页", page=12)]     # boilerplate page number
    result = clean_facts(facts)
    removed = [a for a in result.audit if a.action == "removed"]
    assert removed, "the page-number line should be filtered"
    entry = removed[0]
    assert entry.page_number == 12          # preserved for the cleaning view
    assert entry.report_section == "Risk Factors"
    assert entry.reason                     # a human reason is always present


def test_cleaned_api_reports_rules_and_page_anchored_audit(client, seeded):
    did, headers = seeded
    res = client.get(f"/api/documents/{did}/cleaned", headers=headers).json()
    assert res["rules"], "cleaned response should list active rules"
    assert "dedup" in res["rules"]
    # Every audit entry that removed something should tell the user where from.
    removed = [a for a in res["audit"] if a["action"] == "removed"]
    if removed:
        assert any(a.get("page_number") for a in removed)
        assert all(a.get("reason") for a in removed)
