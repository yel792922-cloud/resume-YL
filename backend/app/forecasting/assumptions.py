"""External scenario assumptions for forecasting (v4.1).

These broaden each scenario beyond the report's internal financial trend with
qualitative macro / market drivers. They are **assumptions, not facts**: the
repo has no external market/macro data source, so these describe the stance each
scenario takes, not observed conditions. They are surfaced separately from the
source-cited metric evidence so users never mistake them for report claims.
"""
from __future__ import annotations

from app.models.schemas import ScenarioAssumptions

EXTERNAL_NOTE = (
    "External factors below are scenario assumptions, not facts from this report "
    "(no external market/macro data source is available)."
)

# One short bullet per driver dimension, framed by scenario stance.
_EXTERNAL: dict[str, list[str]] = {
    "base": [
        "Market: broadly stable demand (no major expansion or contraction assumed)",
        "Macroeconomy: steady conditions, no shock",
        "Regulation: no significant policy change assumed",
        "Competition: intensity roughly unchanged",
        "FX: relatively stable exchange rates",
        "Input / commodity costs: broadly stable",
        "Public sentiment: neutral",
    ],
    "bull": [
        "Market: expansion / new demand tailwinds",
        "Macroeconomy: supportive backdrop",
        "Regulation: easing or favorable policy",
        "Competition: contained competitive pressure",
        "FX: favorable currency trends",
        "Input / commodity costs: easing cost pressure",
        "Public sentiment: positive catalysts",
    ],
    "bear": [
        "Market: contraction / softening demand",
        "Macroeconomy: headwinds or slowdown",
        "Regulation: tighter rules / compliance pressure",
        "Competition: intensifying competition",
        "FX: adverse currency volatility",
        "Input / commodity costs: rising cost pressure",
        "Public sentiment: reputational / sentiment risk",
    ],
}


def external_assumptions() -> list[ScenarioAssumptions]:
    return [ScenarioAssumptions(scenario=s, external_factors=f) for s, f in _EXTERNAL.items()]
