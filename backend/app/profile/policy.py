"""Report policy — the *active* analysis behavior derived from a report profile.

The profile (business structure, geography, industry, complexity) is turned into
a concrete :class:`ReportPolicy` that downstream analysis actually reads: how
aggressively to merge/dedupe, how much scope to preserve, how strict cleaning
and classification should be, which metric families to emphasize, and which
external forecast drivers matter for this kind of company.

This is the difference between the profile being a *label* and being a *policy*:
every field here changes real backend behavior (see ``analysis.py``,
``metric_kind.py``, and ``forecasting/service.py``).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.cleaning.rules import CleaningConfig

# Metric families to surface first, by industry.
_FAMILIES: dict[str, list[str]] = {
    "bank": ["ratio", "regulatory", "amount"],
    "insurance": ["ratio", "regulatory", "amount"],
    "hospitality": ["occupancy", "pricing", "ratio", "amount"],
    "internet": ["segment_total", "user", "ratio", "amount"],
    "saas": ["segment_total", "user", "ratio", "amount"],
    "manufacturing": ["amount", "segment_total", "ratio"],
    "retail": ["ratio", "amount", "segment_total"],
}
_DEFAULT_FAMILIES = ["amount", "ratio", "segment_total"]

# Suggested Custom-scenario external-factor weights (-2..+2) an analyst of this
# kind of company would typically start from. Suggestions only — never auto-applied.
_DRIVER_WEIGHTS: dict[str, dict[str, int]] = {
    "bank": {"interest_rates": 2, "regulatory": 1, "macro": 1},
    "insurance": {"interest_rates": 1, "regulatory": 1, "macro": 1},
    "hospitality": {"consumer_demand": 1, "macro": 1, "market_expansion": 1},
    "internet": {"regulatory": -1, "competition": 1, "consumer_demand": 1},
    "saas": {"competition": 1, "consumer_demand": 1, "market_expansion": 1},
    "manufacturing": {"input_cost": -1, "supply_chain": -1, "macro": 1},
    "retail": {"consumer_demand": 1, "input_cost": -1, "competition": 1},
}


@dataclass(frozen=True)
class ReportPolicy:
    merge_aggressiveness: str          # aggressive | conservative
    scope_preservation: str            # low | high
    unit_inference_threshold: str      # permissive | conservative
    cleaning_strictness: str           # strict | lenient
    conservative_classification: bool
    preferred_metric_families: list[str]
    forecast_driver_weights: dict[str, int]
    notes: list[str] = field(default_factory=list)

    def cleaning_config(self) -> CleaningConfig:
        """Translate the policy into a concrete cleaning configuration."""
        strict = self.cleaning_strictness == "strict"
        return CleaningConfig(
            # Complex reports preserve context; simple reports merge more.
            merge_strength="preserve" if self.merge_aggressiveness == "conservative" else "standard",
            # Strict (simple reports) trims more boilerplate / low-value rows;
            # lenient (complex) keeps more context.
            min_informative_word_chars=8 if strict else 5,
            min_numeric_confidence=0.30 if strict else 0.20,
        )


def _is_complex(profile) -> bool:
    if not profile:
        return False
    return (
        getattr(profile, "complexity", "simple") == "complex"
        or getattr(profile, "business_structure", "") in ("multi", "conglomerate")
        or getattr(profile, "geo_scope", "") in ("multi_region", "global")
    )


def policy_for(profile) -> ReportPolicy:
    """Derive the active analysis policy from a (possibly ``None``) profile."""
    complex_report = _is_complex(profile)
    industry = getattr(profile, "industry", "auto") if profile else "auto"
    families = _FAMILIES.get(industry, _DEFAULT_FAMILIES)
    weights = dict(_DRIVER_WEIGHTS.get(industry, {}))

    notes: list[str] = []
    if complex_report:
        notes.append("Grouping: scope-preserving — repeated labels kept separate across tables/segments.")
        notes.append("Cleaning: conservative — more context retained, dedup only within the same scope.")
        notes.append("Classification: conservative — weak signals stay 'uncertain' rather than being forced.")
        notes.append("Units: conservative inference threshold.")
    else:
        notes.append("Grouping: aggressive — equivalent company-level metrics merged, simpler view.")
        notes.append("Cleaning: strict — more boilerplate/low-value rows removed.")
        notes.append("Classification: permissive.")
        notes.append("Units: slightly more inference allowed.")
    if industry not in ("auto", "unknown", "other"):
        notes.append(f"Forecast emphasis for '{industry}': {', '.join(families)}.")

    return ReportPolicy(
        merge_aggressiveness="conservative" if complex_report else "aggressive",
        scope_preservation="high" if complex_report else "low",
        unit_inference_threshold="conservative" if complex_report else "permissive",
        cleaning_strictness="lenient" if complex_report else "strict",
        conservative_classification=complex_report,
        preferred_metric_families=families,
        forecast_driver_weights=weights,
        notes=notes,
    )
