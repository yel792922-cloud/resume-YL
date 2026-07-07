"""Metric-kind classification + the ratio/growth-vs-amount extraction guard."""
from __future__ import annotations

from app.models.fact import FactCategory
from app.normalization.metric_kind import (
    AMOUNT, GROWTH, PER_SHARE, RATIO, SEGMENT_TOTAL, USER,
    classify_kind, is_mislabeled_amount,
)


# ---------------------------- guard ----------------------------

def test_growth_and_proportion_rows_not_mapped_to_amount():
    assert is_mislabeled_amount("营业收入增长率", "revenue") is True
    assert is_mislabeled_amount("收入占比", "revenue") is True
    assert is_mislabeled_amount("Revenue growth rate", "revenue") is True
    # A genuine amount row is fine.
    assert is_mislabeled_amount("营业收入", "revenue") is False
    assert is_mislabeled_amount("Total revenue", "revenue") is False


def test_guard_only_applies_to_amount_concepts():
    # gross_margin is a percent concept, not an amount — never guarded away.
    assert is_mislabeled_amount("毛利率", "gross_margin") is False
    assert is_mislabeled_amount("每股收益", "eps") is False


# ---------------------------- classify_kind ----------------------------

def test_classify_amounts_and_ratios():
    assert classify_kind(FactCategory.INCOME_STATEMENT, "revenue", "营业收入", "亿元") == AMOUNT
    assert classify_kind(FactCategory.INCOME_STATEMENT, "gross_margin", "毛利率", "%") == RATIO
    assert classify_kind(FactCategory.INCOME_STATEMENT, "eps", "每股收益", "元") == PER_SHARE


def test_growth_and_proportion_labels_classify_correctly():
    assert classify_kind(FactCategory.INCOME_STATEMENT, "revenue", "营业收入增长率", "%") == GROWTH
    assert classify_kind(FactCategory.INCOME_STATEMENT, "revenue", "收入占比", "%") == RATIO


def test_segment_and_user_kinds():
    assert classify_kind(FactCategory.BUSINESS, "segment_revenue", "游戏", "亿元") == SEGMENT_TOTAL
    assert classify_kind(FactCategory.BUSINESS, "user_metric", "月活跃用户", None) == USER


def test_regulatory_label_detected():
    from app.normalization.metric_kind import REGULATORY
    assert classify_kind(FactCategory.BALANCE_SHEET, None, "资本充足率", "%") == REGULATORY


def test_seed_facts_have_kinds(client, seeded):
    did, headers = seeded
    facts = client.get(f"/api/documents/{did}/facts", headers=headers).json()
    by_concept = {f["concept_id"]: f for f in facts if f["concept_id"]}
    assert by_concept["revenue"]["metric_kind"] == "amount"
    assert by_concept["gross_margin"]["metric_kind"] == "ratio"
    assert by_concept["eps"]["metric_kind"] == "per_share"
    assert by_concept["segment_revenue"]["metric_kind"] == "segment_total"
