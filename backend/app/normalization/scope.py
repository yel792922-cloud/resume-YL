"""Metric scope — the context that distinguishes same-named metrics.

For complex conglomerates (e.g. Tencent), a report prints "Revenue" or
"Gross profit" many times at *different scopes*: the consolidated total, a
business segment, a geography, a per-share figure. The flat concept id alone
("revenue") cannot tell these apart, so we derive an explicit :class:`MetricScope`
from the fact's already-stored context (its raw label, report section and
category).

Deriving — rather than storing a new column — keeps this a pure, non-destructive
view over existing fields, so it works on already-extracted data with no schema
migration. The *same* function is used at three points so behaviour is
consistent everywhere:

  * extraction dedup — different scopes must not collapse to one row;
  * cleaning dedup   — only truly-equivalent facts (same scope) merge;
  * serialization    — the UI/exports show the scope for disambiguation.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from app.models.fact import FactCategory

# Scope types (stable string values — surfaced in the API and UI).
CONSOLIDATED = "consolidated"
SEGMENT = "segment"
GEOGRAPHY = "geography"
PER_SHARE = "per_share"
UNSCOPED = ""

# Section / label cues (bilingual). Matched case-insensitively.
_SEGMENT_CUE = re.compile(r"分部|分业务|分業務|业务分部|業務分部|segment|business line|by segment", re.I)
_GEO_CUE = re.compile(r"分地区|分地區|分区域|分區域|地区|地區|区域|區域|geograph|by region|by geography", re.I)
_CONSOLIDATED_CUE = re.compile(r"合并|合併|consolidated|group total", re.I)

_STATEMENT_CATEGORIES = {
    FactCategory.INCOME_STATEMENT.value,
    FactCategory.BALANCE_SHEET.value,
    FactCategory.CASH_FLOW.value,
}


@dataclass(frozen=True)
class MetricScope:
    """A metric's reporting scope plus a human-readable label for it."""

    scope_type: str   # consolidated | segment | geography | per_share | ""
    scope_label: str  # e.g. "Consolidated total", a segment or region name


def _cat_value(category) -> str:
    return category.value if hasattr(category, "value") else str(category)


def derive_scope(
    category,
    concept_id: str | None,
    raw_label: str | None,
    report_section: str | None,
) -> MetricScope:
    """Classify a fact's scope from the context we already store.

    The rules are intentionally simple and deterministic so the classification
    stays auditable. Order matters: explicit segment/geography evidence wins over
    the consolidated default that statement lines fall back to.
    """
    cat = _cat_value(category)
    section = (report_section or "").strip()
    label = (raw_label or "").strip()
    haystack = f"{section} {label}"

    # Business breakdowns keep their own line label as the scope (the segment /
    # region name), which is exactly what makes two same-named rows distinct.
    if concept_id == "segment_revenue" or _SEGMENT_CUE.search(haystack):
        return MetricScope(SEGMENT, label or section)
    if concept_id == "geographic_revenue" or _GEO_CUE.search(haystack):
        return MetricScope(GEOGRAPHY, label or section)

    # Per-share figures are their own scope (never a consolidated currency total).
    if concept_id == "eps":
        return MetricScope(PER_SHARE, "Per share")

    # Statement lines are consolidated totals unless marked otherwise above.
    if cat in _STATEMENT_CATEGORIES:
        return MetricScope(CONSOLIDATED, "Consolidated total")

    return MetricScope(UNSCOPED, "")
