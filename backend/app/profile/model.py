"""Report-profile model + auto-detection.

The profile is intentionally small and forgiving: a few enumerated options plus
free-form ``auto``/``unknown``. User selections are *hints*; auto-detection fills
the rest and always produces a human-readable rationale so the UI can explain
*why* a report is treated as simple or complex.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field

from app.models.fact import ExtractedFact, FactCategory

# ---- Option vocabularies (stable ids; UI localizes labels) ----
BUSINESS_STRUCTURES = ("single", "multi", "conglomerate", "auto", "unknown")
GEO_SCOPES = ("single_region", "multi_region", "global", "auto", "unknown")
INDUSTRIES = (
    "bank", "insurance", "hospitality", "internet", "saas", "retail",
    "manufacturing", "other", "auto", "unknown",
)
REPORT_TYPES = ("annual", "interim", "quarterly", "other", "auto", "unknown")

# Industry keyword cues (bilingual), scanned over company name + fact text.
_INDUSTRY_CUES: tuple[tuple[str, str], ...] = (
    ("bank", r"银行|bank|存款|贷款|净息差|资本充足|deposits|loans|net interest margin"),
    ("insurance", r"保险|寿险|财险|insurance|premiums|保费|偿付能力|solvency"),
    ("hospitality", r"酒店|旅游|度假|入住率|hotel|resort|hospitality|occupancy|travel"),
    ("internet", r"互联网|平台|广告|游戏|社交|internet|platform|advertising|MAU|DAU|游戏收入"),
    ("saas", r"云|订阅|SaaS|软件|subscription|cloud|ARR|seats"),
    ("retail", r"零售|门店|电商|retail|stores|same-store|e-commerce|GMV"),
    ("manufacturing", r"制造|产能|产量|工厂|manufactur|capacity|production|order book|出货"),
)


@dataclass
class ReportProfile:
    business_structure: str = "auto"
    geo_scope: str = "auto"
    industry: str = "auto"
    report_type: str = "auto"
    source: str = "auto"            # user | auto | mixed
    complexity: str = "simple"      # simple | complex
    rationale: list[str] = field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)


def profile_options() -> dict[str, list[str]]:
    """The selectable option ids, for the upload UI."""
    return {
        "business_structure": list(BUSINESS_STRUCTURES),
        "geo_scope": list(GEO_SCOPES),
        "industry": list(INDUSTRIES),
        "report_type": list(REPORT_TYPES),
    }


def profile_from_json(raw: str | None) -> ReportProfile | None:
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return None
    known = {f for f in ReportProfile().__dataclass_fields__}
    return ReportProfile(**{k: v for k, v in data.items() if k in known})


def _clean(value: str | None, allowed: tuple[str, ...]) -> str:
    v = (value or "auto").strip().lower()
    return v if v in allowed else "auto"


def _detect_industry(company: str | None, facts: list[ExtractedFact]) -> str | None:
    import re

    haystack = " ".join(
        [company or ""]
        + [f.raw_label or "" for f in facts]
        + [(f.source_text_snippet or "")[:120] for f in facts[:60]]
    )
    for industry, pattern in _INDUSTRY_CUES:
        if re.search(pattern, haystack, re.I):
            return industry
    return None


def infer_profile(
    document,
    facts: list[ExtractedFact],
    hints: ReportProfile | None = None,
) -> ReportProfile:
    """Merge user hints with signals auto-detected from the extracted facts.

    User-provided (non-auto) fields win; everything else is inferred. Always
    records a rationale so the decision is explainable in the UI.
    """
    hints = hints or ReportProfile()
    rationale: list[str] = []

    has_segment = any(f.concept_id == "segment_revenue" for f in facts)
    has_geo = any(f.concept_id == "geographic_revenue" for f in facts)
    n_segments = len({f.raw_label for f in facts if f.concept_id == "segment_revenue"})
    n_geos = len({f.raw_label for f in facts if f.concept_id == "geographic_revenue"})

    # --- Business structure ---
    hb = _clean(hints.business_structure, BUSINESS_STRUCTURES)
    if hb not in ("auto", "unknown"):
        business = hb
        rationale.append(f"Business structure set by user: {business}.")
    else:
        if n_segments >= 4:
            business = "conglomerate"
        elif has_segment:
            business = "multi"
        else:
            business = "single"
        rationale.append(
            f"Auto: {n_segments} business segment(s) detected → {business}-business."
            if has_segment else "Auto: no business-segment breakdown found → single-business."
        )

    # --- Geographic scope ---
    hg = _clean(hints.geo_scope, GEO_SCOPES)
    if hg not in ("auto", "unknown"):
        geo = hg
        rationale.append(f"Geographic scope set by user: {geo}.")
    else:
        geo = "multi_region" if has_geo else "single_region"
        rationale.append(
            f"Auto: {n_geos} geography breakdown(s) detected → multi-region."
            if has_geo else "Auto: no geography breakdown found → single-region."
        )

    # --- Industry ---
    hi = _clean(hints.industry, INDUSTRIES)
    if hi not in ("auto", "unknown"):
        industry = hi
        rationale.append(f"Industry set by user: {industry}.")
    else:
        detected = _detect_industry(getattr(document, "company_name", None), facts)
        industry = detected or "other"
        if detected:
            rationale.append(f"Auto: industry cues suggest '{industry}'.")

    # --- Report type (fall back to the document's own detected type) ---
    hr = _clean(hints.report_type, REPORT_TYPES)
    report_type = hr if hr not in ("auto", "unknown") else getattr(
        getattr(document, "report_type", None), "value", "other"
    )

    complexity = "complex" if business in ("multi", "conglomerate") or geo != "single_region" else "simple"
    rationale.append(f"Treated as a {complexity} report.")

    user_set = any(
        _clean(getattr(hints, f), opts) not in ("auto", "unknown")
        for f, opts in (
            ("business_structure", BUSINESS_STRUCTURES),
            ("geo_scope", GEO_SCOPES),
            ("industry", INDUSTRIES),
            ("report_type", REPORT_TYPES),
        )
    )
    source = "mixed" if user_set else "auto"

    return ReportProfile(
        business_structure=business,
        geo_scope=geo,
        industry=industry,
        report_type=report_type,
        source=source,
        complexity=complexity,
        rationale=rationale,
    )
