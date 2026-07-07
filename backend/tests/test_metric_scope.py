"""Metric scope modeling: scope derivation, scope-aware dedup, segment capture.

These guard the refinement that keeps same-named metrics distinct by scope
(consolidated vs segment vs geography vs per-share) for complex conglomerates.
"""
from __future__ import annotations

from app.cleaning import clean_facts
from app.models.fact import ExtractedFact, FactCategory
from app.normalization.scope import (
    CONSOLIDATED,
    GEOGRAPHY,
    PER_SHARE,
    SEGMENT,
    derive_scope,
)


def _fact(id_, concept, value, *, category=FactCategory.INCOME_STATEMENT,
          unit="亿元", conf=0.9, raw_label=None, section=None, period="2024 FY"):
    return ExtractedFact(
        id=id_,
        document_id="doc1",
        category=category,
        concept_id=concept,
        metric_name=(concept or "x").title(),
        raw_label=raw_label,
        metric_value=value,
        unit=unit,
        confidence_score=conf,
        report_period=period,
        report_section=section,
        source_page_number=1,
        source_text_snippet=raw_label or f"{concept} {value}",
    )


# ---------------------------- scope derivation ----------------------------

def test_statement_line_is_consolidated():
    s = derive_scope(FactCategory.INCOME_STATEMENT, "revenue", "营业收入 Revenue", "Financial Statements")
    assert s.scope_type == CONSOLIDATED
    assert s.scope_label


def test_segment_scope_from_concept_and_section():
    s = derive_scope(FactCategory.BUSINESS, "segment_revenue", "增值服务 Value-Added Services", "Segment Revenue")
    assert s.scope_type == SEGMENT
    assert s.scope_label == "增值服务 Value-Added Services"   # the line label IS the scope


def test_geography_scope_from_section_cue():
    s = derive_scope(FactCategory.BUSINESS, "geographic_revenue", "中国大陆 Mainland China", "Geographic Revenue")
    assert s.scope_type == GEOGRAPHY


def test_eps_is_per_share_scope():
    s = derive_scope(FactCategory.INCOME_STATEMENT, "eps", "每股收益 EPS", "Financial Statements")
    assert s.scope_type == PER_SHARE


# ---------------------------- scope-aware dedup ----------------------------

def test_same_name_different_scope_not_merged():
    # Same concept + same value + same unit, but one is the consolidated total
    # and one is a segment line — these are NOT duplicates.
    consolidated = _fact(1, "revenue", 100.0, section="Consolidated Income Statement")
    segment = _fact(2, "revenue", 100.0, category=FactCategory.BUSINESS,
                    raw_label="游戏 Games", section="Segment Revenue")
    result = clean_facts([consolidated, segment])
    assert {f.id for f in result.retained} == {1, 2}


def test_two_distinct_segments_not_merged():
    a = _fact(1, "segment_revenue", 3120.5, category=FactCategory.BUSINESS,
              raw_label="增值服务", section="Segment Revenue")
    b = _fact(2, "segment_revenue", 1987.4, category=FactCategory.BUSINESS,
              raw_label="网络广告", section="Segment Revenue")
    result = clean_facts([a, b])
    assert len(result.retained) == 2


def test_different_periods_not_merged():
    cur = _fact(1, "revenue", 6096.9, period="2024 FY")
    prior = _fact(2, "revenue", 6096.9, period="2023 FY")
    result = clean_facts([cur, prior])
    assert len(result.retained) == 2


def test_truly_equivalent_facts_still_merge():
    # Identical scope + period + value → the lower-confidence copy is deduped.
    a = _fact(1, "revenue", 6096.9, conf=0.9, section="Financial Statements")
    b = _fact(2, "revenue", 6096.9, conf=0.6, section="Financial Statements")
    result = clean_facts([a, b])
    assert len(result.retained) == 1 and result.retained[0].id == 1


# ---------------------------- integration (seed) --------------------------

def test_seed_surfaces_segment_breakdown_with_units_and_scope(client, seeded):
    did, headers = seeded
    facts = client.get(f"/api/documents/{did}/facts", headers=headers).json()

    segments = [f for f in facts if f["concept_id"] == "segment_revenue"]
    assert len(segments) >= 3, "segment breakdown rows should be captured, not dropped"
    # Each segment keeps a distinct scope label and an explicit unit.
    assert all(f["scope_type"] == "segment" for f in segments)
    assert len({f["scope_label"] for f in segments}) == len(segments)
    assert all(f["unit"] for f in segments), "segment currency facts must carry a unit"

    # Consolidated revenue is still present and marked consolidated.
    consolidated = [f for f in facts if f["concept_id"] == "revenue"]
    assert consolidated and all(f["scope_type"] == "consolidated" for f in consolidated)


def test_export_csv_has_scope_columns(client, seeded):
    did, headers = seeded
    header_line = client.get(f"/api/documents/{did}/export.csv", headers=headers).text.splitlines()[0]
    assert "scope_type" in header_line and "scope_label" in header_line
