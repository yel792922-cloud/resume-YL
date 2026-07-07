"""Metric-kind classification — what *type* of number a fact is.

The concept layer says *which* line item a value belongs to (revenue, EPS, …).
This module says what *kind* of quantity it is — an amount, a ratio, a growth
rate, a per-share figure, a count, a segment/geography total, a regulatory/
capital metric, or an operational/user metric.

This matters because a report prints "营业收入" (an amount) next to
"营业收入增长率" (a growth rate) and "收入占比" (a proportion). Those must NOT
collapse into the same amount concept. Two jobs live here:

* :func:`classify_kind` — label a fact's kind (derived, not stored).
* :func:`is_mislabeled_amount` — an extraction guard so a ratio/growth/
  proportion row never gets mapped onto a currency amount concept.
"""
from __future__ import annotations

import re

from app.models.fact import FactCategory
from app.normalization.concepts import concept_by_id

# Kind values (stable strings surfaced in the API/UI).
AMOUNT = "amount"
RATIO = "ratio"
GROWTH = "growth"
PER_SHARE = "per_share"
COUNT = "count"
SEGMENT_TOTAL = "segment_total"
GEOGRAPHY_TOTAL = "geography_total"
REGULATORY = "regulatory"
USER = "user"
UNCERTAIN = "uncertain"

# Label markers (bilingual). Order matters: growth/proportion are more specific
# than a bare "率/ratio", so they are tested first.
_GROWTH = re.compile(r"增长率|增速|增幅|同比增长|环比增长|同比|环比|growth\s*rate|yoy|qoq|y/y|q/q", re.I)
_PROPORTION = re.compile(r"占比|占.*比重|比重|占.*百分比|share\s+of|proportion|as\s+%\s+of|% of", re.I)
_RATIO = re.compile(r"率|比率|倍数|ratio|margin|turnover days|per\s+\w+\b", re.I)
_REGULATORY = re.compile(
    r"资本充足率|核心一级|一级资本|拨备覆盖率|不良(贷款)?率|流动性覆盖|偿付能力|"
    r"capital adequacy|tier\s*1|cet1|npl|coverage ratio|solvency|liquidity coverage|rwa",
    re.I,
)
_USER_OP = re.compile(
    r"用户|活跃|付费|订阅|会员|入住率|客房|装机|门店|mau|dau|arpu|subscribers?|"
    r"active users|occupancy|paying users|installs?|stores?",
    re.I,
)

# Concept ids that are their own kind regardless of label wording.
_KIND_BY_CONCEPT = {
    "eps": PER_SHARE,
    "gross_margin": RATIO,
    "segment_revenue": SEGMENT_TOTAL,
    "geographic_revenue": GEOGRAPHY_TOTAL,
    "user_metric": USER,
}


def _unit_hint(concept_id: str | None) -> str | None:
    c = concept_by_id(concept_id) if concept_id else None
    return c.unit_hint if c else None


def is_amount_concept(concept_id: str | None) -> bool:
    """True for currency line items (revenue, profit, assets, …)."""
    return _unit_hint(concept_id) == "currency" and concept_id not in (
        "segment_revenue", "geographic_revenue",
    )


def is_mislabeled_amount(raw_label: str | None, concept_id: str | None) -> bool:
    """Guard: would mapping ``raw_label`` onto an amount concept be wrong?

    A row like "营业收入增长率" or "收入占比" contains an amount alias but is a
    growth rate / proportion — it must not be extracted as the amount concept.
    """
    if not raw_label or not is_amount_concept(concept_id):
        return False
    label = raw_label
    return bool(_GROWTH.search(label) or _PROPORTION.search(label) or _RATIO.search(label))


def classify_kind(
    category,
    concept_id: str | None,
    raw_label: str | None,
    unit: str | None,
    is_percent: bool = False,
) -> str:
    """Best-effort kind for a fact. Falls back to ``uncertain`` when unsure."""
    label = raw_label or ""

    # 1) Label wording is the strongest signal for ratio-vs-amount confusion.
    if _GROWTH.search(label):
        return GROWTH
    if _PROPORTION.search(label):
        return RATIO
    if _REGULATORY.search(label):
        return REGULATORY
    if _USER_OP.search(label):
        return USER

    # 2) Concept-driven kinds.
    if concept_id in _KIND_BY_CONCEPT:
        return _KIND_BY_CONCEPT[concept_id]

    hint = _unit_hint(concept_id)
    if hint == "percent" or is_percent or unit == "%":
        return RATIO
    if hint == "shares":
        return PER_SHARE
    if hint == "count":
        return COUNT
    if hint == "currency":
        return AMOUNT

    # 3) No concept — lean on the label / category, else stay honest.
    if _RATIO.search(label):
        return RATIO
    if category == FactCategory.BUSINESS:
        return USER
    return UNCERTAIN
