"""Extract qualitative business signals: risk factors, management commentary,
guidance. These are non-numeric facts (``value_text`` holds the snippet) but
still fully source-traced to page + bounding box.
"""
from __future__ import annotations

import re

from app.extraction.base import FactDraft
from app.models.fact import FactCategory
from app.normalization.dictionary import detect_language
from app.sourcemap.highlight import locate_snippet

# Section heading cues (bilingual).
_SECTION_CUES: dict[FactCategory, tuple[str, ...]] = {
    FactCategory.RISK: (
        "风险因素", "风险提示", "主要风险", "重大风险",
        "risk factors", "principal risks", "key risks", "risk management",
    ),
    FactCategory.MANAGEMENT: (
        "管理层讨论与分析", "管理层讨论", "经营情况讨论", "董事长致辞", "管理层报告",
        "management discussion", "md&a", "management's discussion", "chairman's statement",
        "business review", "对未来的展望", "经营策略",
    ),
    FactCategory.GUIDANCE: (
        "业绩指引", "全年指引", "未来展望", "经营目标", "盈利预测",
        "guidance", "outlook", "full-year guidance", "we expect", "our outlook",
    ),
}

# Sentence-level cues that flag a signal even without a section heading.
_SENTENCE_CUES: dict[FactCategory, tuple[str, ...]] = {
    FactCategory.GUIDANCE: (
        "预计", "预期", "展望", "指引", "有望", "计划实现",
        "we expect", "we anticipate", "outlook", "guidance", "target", "forecast",
    ),
    FactCategory.RISK: (
        "风险", "不确定", "可能导致", "面临", "挑战",
        "risk", "uncertain", "may adversely", "could result", "exposure",
    ),
}

# Split on CJK sentence punctuation, on English ". " (space-separated so
# "25.6%" isn't broken), and on newlines.
_SENT_SPLIT = re.compile(r"(?<=[。！？；;])\s*|(?<=[.!?])\s+|\n+")
_MAX_PER_CATEGORY = 8


def _label_for(category: FactCategory) -> tuple[str, str]:
    return {
        FactCategory.RISK: ("Risk Factor", "风险提示"),
        FactCategory.MANAGEMENT: ("Management Commentary", "管理层讨论"),
        FactCategory.GUIDANCE: ("Guidance", "业绩指引"),
    }[category]


def _section_on_page(text: str) -> FactCategory | None:
    low = text.lower()
    for category, cues in _SECTION_CUES.items():
        if any(cue in low or cue in text for cue in cues):
            return category
    return None


def _make_draft(category: FactCategory, sentence: str, page_number: int, words: list[dict]) -> FactDraft:
    name_en, name_zh = _label_for(category)
    return FactDraft(
        category=category,
        concept_id=None,
        metric_name=name_en,
        metric_label=name_zh,
        raw_label=None,
        language=detect_language(sentence),
        value_text=sentence.strip()[:400],
        source_page_number=page_number,
        report_section=name_en,
        source_text_snippet=sentence.strip()[:400],
        source_bbox=locate_snippet(words, sentence.strip()[:50]),
        confidence_score=0.5,
        extraction_method="section",
    )


def extract_signals(
    page_number: int,
    page_text: str,
    words: list[dict],
    counts: dict[FactCategory, int],
) -> list[FactDraft]:
    """Extract risk / management / guidance snippets from a page.

    ``counts`` tracks how many of each category we've emitted document-wide so
    we cap the volume and keep the highest-signal snippets.
    """
    drafts: list[FactDraft] = []
    if not page_text.strip():
        return drafts

    section = _section_on_page(page_text)
    sentences = [s.strip() for s in _SENT_SPLIT.split(page_text) if len(s.strip()) >= 10]

    for sentence in sentences:
        for category, cues in _SENTENCE_CUES.items():
            if counts.get(category, 0) >= _MAX_PER_CATEGORY:
                continue
            low = sentence.lower()
            hit = any(cue in low or cue in sentence for cue in cues)
            # A management section contributes its sentences as commentary.
            if not hit and section == FactCategory.MANAGEMENT and category == FactCategory.GUIDANCE:
                continue
            if hit:
                drafts.append(_make_draft(category, sentence, page_number, words))
                counts[category] = counts.get(category, 0) + 1
                break

    # Management commentary: capture the lead sentences of a management section.
    if section == FactCategory.MANAGEMENT and counts.get(FactCategory.MANAGEMENT, 0) < _MAX_PER_CATEGORY:
        for sentence in sentences[:3]:
            if counts.get(FactCategory.MANAGEMENT, 0) >= _MAX_PER_CATEGORY:
                break
            drafts.append(_make_draft(FactCategory.MANAGEMENT, sentence, page_number, words))
            counts[FactCategory.MANAGEMENT] = counts.get(FactCategory.MANAGEMENT, 0) + 1

    return drafts
