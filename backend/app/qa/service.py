"""Compose a concise, grounded, cited answer from retrieved evidence.

Extractive only — no LLM, no general knowledge. Each answer is built from
retrieved facts/snippets and reports an evidence-strength level; when the report
lacks supporting evidence, the answer is conservative and ``insufficient`` is set.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.forecasting.engine import parse_prior_from_snippet
from app.models.document import Document
from app.models.fact import ExtractedFact
from app.models.schemas import AnswerResponse, EvidenceItem, SourceRef
from app.qa import intent as I
from app.qa.intent import classify
from app.qa.retrieval import gather
from app.search.search import _fact_to_out

# Concise bilingual framing. Evidence text stays in the report's native language.
_T = {
    "no_reason": {
        "zh": "报告未明确说明变动原因。",
        "en": "The report does not state an explicit reason.",
    },
    "per_mgmt": {"zh": "管理层表示：", "en": "Management notes:"},
    "vs_prior": {"zh": "相较上期：", "en": "Versus the prior period:"},
    "risk_intro": {"zh": "报告提示的主要风险：", "en": "The report highlights these main risks:"},
    "general_intro": {"zh": "根据报告中最相关的内容：", "en": "Based on the most relevant evidence in the report:"},
    "insufficient": {
        "zh": "本报告缺少足够证据以自信回答该问题。",
        "en": "This report does not contain enough evidence to answer this confidently.",
    },
    "conservative_note": {
        "zh": "证据有限，回答较为保守，且仅基于本报告内容。",
        "en": "Evidence is limited; this answer is conservative and based only on this report.",
    },
    "rose": {"zh": "上升", "en": "rose"},
    "fell": {"zh": "下降", "en": "fell"},
    "flat": {"zh": "基本持平", "en": "was roughly flat"},
    "from": {"zh": "较上期", "en": "from"},
    "healthy_cash": {"zh": "经营现金流为正", "en": "operating cash flow is positive"},
    "improving": {"zh": "且较上期改善", "en": "and improving versus the prior period"},
    "weakening": {"zh": "但较上期走弱", "en": "but weaker than the prior period"},
    "curr_ratio_ok": {"zh": "流动比率大于 1，短期偿债能力尚可", "en": "current ratio above 1 (adequate short-term liquidity)"},
    "curr_ratio_low": {"zh": "流动比率低于 1，需关注短期偿债", "en": "current ratio below 1 (watch short-term liquidity)"},
}


def _tr(key: str, lang: str) -> str:
    return _T[key]["zh" if lang == "zh" else "en"]


def _is_percent(f: ExtractedFact) -> bool:
    return f.unit == "%" or f.concept_id == "gross_margin"


def _label(f: ExtractedFact, lang: str) -> str:
    return (f.metric_label or f.metric_name) if lang == "zh" else f.metric_name


def _value(f: ExtractedFact) -> str:
    if f.value_text:
        return f.value_text
    if f.metric_value is not None:
        v = f"{f.metric_value:g}"
        return f"{v} {f.unit}" if f.unit and f.unit != "%" else v
    return "—"


def _conf_level(score: float) -> str:
    return "high" if score >= 0.8 else "medium" if score >= 0.55 else "low"


def _delta_clause(f: ExtractedFact, lang: str) -> str | None:
    if f.metric_value is None:
        return None
    is_pct = _is_percent(f)
    prior = parse_prior_from_snippet(f.source_text_snippet, f.metric_value, is_pct)
    if prior is None:
        return None
    frm = _tr("from", lang)
    if is_pct:
        change = f.metric_value - prior
        word = _tr("rose" if change > 0.05 else "fell" if change < -0.05 else "flat", lang)
        return f"{word} {abs(change):.1f}pp ({frm} {prior:g})"
    if prior <= 0 or f.metric_value <= 0:
        return None
    g = (f.metric_value / prior - 1) * 100
    word = _tr("rose" if g > 0.5 else "fell" if g < -0.5 else "flat", lang)
    return f"{word} {abs(g):.1f}% ({frm} {prior:g})"


def _ev_from_fact(f: ExtractedFact, kind: str, lang: str) -> EvidenceItem:
    out = _fact_to_out(f)
    if kind == "fact":
        text = f"{_label(f, lang)}: {_value(f)}"
    else:
        text = (f.value_text or f.source_text_snippet or "").strip()[:280]
    return EvidenceItem(text=text, kind=kind, source=out.source, fact=out, score=f.confidence_score)


def _ev_from_hit(hit) -> EvidenceItem:
    return EvidenceItem(
        text=(hit.snippet or "").strip()[:280],
        kind=hit.kind,
        source=SourceRef(page_number=hit.page_number, section=hit.section, snippet=hit.snippet, bbox=hit.bbox),
        fact=hit.fact,
        score=hit.score,
    )


def _dedupe(items: list[EvidenceItem]) -> list[EvidenceItem]:
    seen: set = set()
    out: list[EvidenceItem] = []
    for it in items:
        key = ((it.source.page_number if it.source else None), (it.text or "")[:60])
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out


def answer_question(db: Session, document: Document, question: str, mode: str = "clean") -> AnswerResponse:
    question = (question or "").strip()
    qi = classify(question)
    lang = "zh" if qi.lang == "zh" else "en"
    r = gather(db, document, qi, question, mode)

    answer = ""
    evidence: list[EvidenceItem] = []
    confidence = "low"
    insufficient = False

    def finish() -> AnswerResponse:
        note = _tr("conservative_note", lang) if (insufficient or confidence == "low") else None
        return AnswerResponse(
            document_id=document.id, question=question, intent=qi.intent,
            answer=answer or _tr("insufficient", lang), confidence=confidence,
            insufficient=insufficient, evidence=_dedupe(evidence)[:6], note=note,
        )

    # ---- RISKS ----
    if qi.intent == I.RISKS:
        if not r.risks:
            insufficient = True
            return finish()
        evidence = [_ev_from_fact(f, "risk", lang) for f in r.risks[:5]]
        answer = _tr("risk_intro", lang) + " " + "; ".join(e.text for e in evidence[:3])
        confidence = "high" if len(r.risks) >= 3 else "medium"
        return finish()

    # ---- WHY a metric changed ----
    if qi.intent == I.WHY_CHANGE and r.concept_facts:
        f = r.concept_facts[0]
        delta = _delta_clause(f, lang)
        head = f"{_label(f, lang)} {delta}." if delta else f"{_label(f, lang)}: {_value(f)}."
        evidence.append(_ev_from_fact(f, "fact", lang))
        if r.drivers:
            d = r.drivers[0]
            evidence.append(_ev_from_fact(d, "management", lang))
            answer = f"{head} {_tr('per_mgmt', lang)} “{(d.value_text or d.source_text_snippet or '')[:180].strip()}”"
            confidence = "high" if (f.confidence_score >= 0.8 and delta) else "medium"
        else:
            answer = f"{head} {_tr('no_reason', lang)}"
            confidence = "medium" if delta else "low"
            insufficient = not delta
        for d in r.drivers[1:3]:
            evidence.append(_ev_from_fact(d, "management", lang))
        return finish()

    # ---- PERIOD-OVER-PERIOD change ----
    if qi.intent == I.PERIOD_CHANGE:
        targets = r.concept_facts or [
            r.best_by_concept[c] for c in ("revenue", "net_profit", "gross_margin", "operating_cash_flow")
            if c in r.best_by_concept
        ]
        parts: list[str] = []
        for f in targets:
            delta = _delta_clause(f, lang)
            if delta:
                parts.append(f"{_label(f, lang)} {delta}")
                evidence.append(_ev_from_fact(f, "fact", lang))
        if parts:
            answer = _tr("vs_prior", lang) + " " + "; ".join(parts[:5]) + "."
            confidence = "high" if len(parts) >= 2 else "medium"
        else:
            insufficient = True
        return finish()

    # ---- CASH-FLOW health ----
    if qi.intent == I.CASH_HEALTH:
        ocf = r.best_by_concept.get("operating_cash_flow")
        fcf = r.best_by_concept.get("free_cash_flow")
        ca = r.best_by_concept.get("current_assets")
        cl = r.best_by_concept.get("current_liabilities")
        if not ocf and not fcf:
            insufficient = True
            return finish()
        clauses: list[str] = []
        anchor = ocf or fcf
        clauses.append(f"{_label(anchor, lang)}: {_value(anchor)}")
        evidence.append(_ev_from_fact(anchor, "fact", lang))
        if anchor.metric_value is not None and anchor.metric_value > 0:
            trend = _delta_clause(anchor, lang)
            note = _tr("healthy_cash", lang)
            if trend and _tr("rose", lang) in trend:
                note += " " + _tr("improving", lang)
            elif trend and _tr("fell", lang) in trend:
                note += " " + _tr("weakening", lang)
            clauses.append(note)
        if ca and cl and cl.metric_value:
            ratio = ca.metric_value / cl.metric_value
            clauses.append(_tr("curr_ratio_ok" if ratio >= 1 else "curr_ratio_low", lang))
            evidence.append(_ev_from_fact(ca, "fact", lang))
            evidence.append(_ev_from_fact(cl, "fact", lang))
        answer = ". ".join(clauses) + "."
        confidence = _conf_level(anchor.confidence_score)
        return finish()

    # ---- METRIC lookup ----
    if qi.intent == I.METRIC_LOOKUP and r.concept_facts:
        f = r.concept_facts[0]
        delta = _delta_clause(f, lang)
        answer = f"{_label(f, lang)}: {_value(f)}" + (f" ({delta})." if delta else ".")
        evidence.append(_ev_from_fact(f, "fact", lang))
        confidence = _conf_level(f.confidence_score)
        return finish()

    # ---- GENERAL fallback: lean on search hits ----
    hits = [h for h in r.text_hits if (h.snippet or "").strip()]
    if hits:
        evidence = [_ev_from_hit(h) for h in hits[:5]]
        answer = _tr("general_intro", lang) + " " + evidence[0].text
        confidence = "medium" if hits[0].score >= 1.0 else "low"
    else:
        insufficient = True
    return finish()
