"""Classify a report question into an intent + target concept(s).

Deterministic keyword/concept routing (bilingual). Keeps Q&A explainable and
dependency-free; the intent selects which evidence the retrieval step gathers.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.normalization.dictionary import detect_language, get_term_matcher

# Intent labels
METRIC_LOOKUP = "metric_lookup"
WHY_CHANGE = "why_change"
PERIOD_CHANGE = "period_change"
CASH_HEALTH = "cash_health"
RISKS = "risks"
GENERAL = "general"

_RISK_KW = ("风险", "隐患", "担忧", "不确定", "risk", "concern", "threat", "headwind")
_WHY_KW = ("为什么", "为何", "原因", "因为", "驱动", "why", "reason", "driver", "drove", "because", "cause", "explain")
_CHANGE_KW = (
    "变化", "增长", "下降", "上升", "下滑", "改善", "恶化", "同比", "环比", "较上期", "变动",
    "change", "changed", "increase", "increased", "decrease", "decreased", "grew", "grow",
    "fell", "fall", "rose", "rise", "improve", "declin", "versus", " vs", "compared", "yoy",
)
_CASH_KW = ("现金流", "现金", "偿债", "流动性", "cash flow", "cashflow", "liquidity", "solvency", "runway")


@dataclass
class QuestionIntent:
    intent: str
    concepts: list[str]      # target concept ids (may be empty)
    lang: str                # zh | en | unknown


def _contains(text: str, kws: tuple[str, ...]) -> bool:
    return any(k in text for k in kws)


def classify(question: str) -> QuestionIntent:
    q = (question or "").lower().strip()
    lang = detect_language(question)

    # Concept(s) mentioned in the question.
    concepts: list[str] = []
    hit = get_term_matcher().find_in(question)
    if hit is not None:
        concepts.append(hit.concept.id)
    if _contains(q, _CASH_KW) and "operating_cash_flow" not in concepts:
        concepts.append("operating_cash_flow")

    has_why = _contains(q, _WHY_KW)
    has_change = _contains(q, _CHANGE_KW)

    # Priority order — most specific first.
    if _contains(q, _RISK_KW):
        intent = RISKS
    elif has_why and concepts:
        intent = WHY_CHANGE
    elif has_change and not _contains(q, _CASH_KW):
        intent = PERIOD_CHANGE
    elif _contains(q, _CASH_KW):
        intent = CASH_HEALTH
    elif concepts:
        intent = METRIC_LOOKUP
    else:
        intent = GENERAL

    return QuestionIntent(intent=intent, concepts=concepts, lang=lang)
