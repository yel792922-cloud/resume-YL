"""Report-profile inference + persistence + hint override."""
from __future__ import annotations

from types import SimpleNamespace

from app.models.fact import ExtractedFact, FactCategory
from app.profile import ReportProfile, infer_profile, profile_from_json


def _seg(label):
    return ExtractedFact(
        document_id="d", category=FactCategory.BUSINESS, concept_id="segment_revenue",
        metric_name="Segment Revenue", raw_label=label, metric_value=1.0,
        confidence_score=0.8, source_text_snippet=label,
    )


def _geo(label):
    return ExtractedFact(
        document_id="d", category=FactCategory.BUSINESS, concept_id="geographic_revenue",
        metric_name="Geographic Revenue", raw_label=label, metric_value=1.0,
        confidence_score=0.8, source_text_snippet=label,
    )


_doc = SimpleNamespace(company_name="Test Co", report_type=SimpleNamespace(value="annual"))


def test_auto_single_business_when_no_segments():
    p = infer_profile(_doc, [], None)
    assert p.business_structure == "single"
    assert p.geo_scope == "single_region"
    assert p.complexity == "simple"
    assert p.source == "auto" and p.rationale


def test_auto_multi_business_and_region():
    facts = [_seg("游戏"), _seg("广告"), _geo("中国"), _geo("海外")]
    p = infer_profile(_doc, facts, None)
    assert p.business_structure == "multi"
    assert p.geo_scope == "multi_region"
    assert p.complexity == "complex"


def test_conglomerate_when_many_segments():
    facts = [_seg(f"seg{i}") for i in range(5)]
    p = infer_profile(_doc, facts, None)
    assert p.business_structure == "conglomerate"


def test_user_hint_overrides_autodetect():
    facts = [_seg("游戏"), _seg("广告")]  # auto would say multi
    p = infer_profile(_doc, facts, ReportProfile(business_structure="single", industry="bank"))
    assert p.business_structure == "single"   # user hint wins
    assert p.industry == "bank"
    assert p.source == "mixed"


def test_industry_autodetected_from_cues():
    doc = SimpleNamespace(company_name="Some Commercial Bank 银行", report_type=SimpleNamespace(value="annual"))
    p = infer_profile(doc, [], None)
    assert p.industry == "bank"


def test_profile_json_roundtrip():
    p = infer_profile(_doc, [_seg("游戏")], None)
    again = profile_from_json(p.to_json())
    assert again.business_structure == p.business_structure
    assert again.rationale == p.rationale


def test_seed_summary_exposes_profile(client, seeded):
    did, headers = seeded
    doc = client.get(f"/api/documents/{did}", headers=headers).json()
    prof = doc["profile"]
    assert prof is not None
    assert prof["business_structure"] == "multi"     # sample has 3 segments
    assert prof["complexity"] == "complex"
    assert prof["rationale"]
