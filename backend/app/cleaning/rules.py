"""Cleaning rules and tunable configuration.

Deterministic, easy-to-tune heuristics. Each rule is a small pure predicate or
normalizer so the behavior stays auditable and adjustable. Grouped here so the
whole cleaning policy lives in one readable place.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class CleaningConfig:
    """Knobs for the cleaning pass. Conservative by default so we never drop
    genuine financial facts. Override per-call to tune later."""

    # A qualitative (section) snippet shorter than this is treated as low-info.
    min_section_snippet_chars: int = 12
    # A snippet must contain at least this many CJK/Latin "word" characters to
    # be considered informative (guards against pure punctuation / page numbers).
    min_informative_word_chars: int = 6
    # Drop numeric-concept facts whose confidence is below this floor.
    min_numeric_confidence: float = 0.25
    enable_boilerplate_filter: bool = True
    enable_dedup: bool = True
    enable_unit_normalization: bool = True


# ---------------------------------------------------------------------------
# Boilerplate / noise patterns (bilingual). Matched against qualitative snippets
# (risk / management / guidance / business text), NOT against numeric concept
# facts — those are always high-value and are never dropped by these rules.
# ---------------------------------------------------------------------------
_BOILERPLATE_PATTERNS: tuple[re.Pattern, ...] = (
    re.compile(r"^\s*第?\s*\d+\s*[页頁]\s*$"),                 # "第 12 页" / "12 页"
    re.compile(r"^\s*page\s*\d+(\s*/\s*\d+)?\s*$", re.I),        # "Page 3", "Page 3/40"
    re.compile(r"^\s*[-—·•\.\s]+\s*$"),                          # rules of dots / dashes
    re.compile(r"^\s*\d+\s*$"),                                   # a bare number (page no.)
    re.compile(r"免责声明|免責聲明|重要提示|特别提示"),           # disclaimers
    re.compile(r"disclaimer|forward[- ]looking statements", re.I),
    re.compile(r"^\s*目\s*录\s*$|^\s*(table of )?contents\s*$", re.I),  # TOC
    re.compile(r"^\s*(项目|項目|item)\s+20\d{2}\s+20\d{2}\s*$", re.I),   # repeated table header row
    re.compile(r"扫描.*二维码|关注.*公众号|请参[见閱阅]"),        # nav / promo boilerplate
)

# Repeated column-header labels that occasionally slip into extraction.
_HEADER_LABELS = {
    "项目", "項目", "item", "单位", "單位", "unit", "合计", "小计", "total", "subtotal",
    "2024", "2023", "2022", "2021", "本期", "上期", "同比", "year", "period",
}

# OCR-garbage heuristic: a token with a high ratio of isolated symbols / no real
# words. We keep this deliberately mild to avoid nuking legitimate content.
_WORD_CHARS = re.compile(r"[0-9A-Za-z一-鿿]")
_LETTERS = re.compile(r"[A-Za-z一-鿿]")


def _informative_char_count(text: str) -> int:
    return len(_WORD_CHARS.findall(text or ""))


def is_boilerplate(snippet: str | None) -> bool:
    if not snippet:
        return True
    s = snippet.strip()
    for pat in _BOILERPLATE_PATTERNS:
        if pat.search(s):
            return True
    # A short snippet that is just a header label (or two) is noise.
    if s.lower() in _HEADER_LABELS:
        return True
    return False

def looks_like_ocr_garbage(snippet: str | None) -> bool:
    if not snippet:
        return True
    s = snippet.strip()
    letters = len(_LETTERS.findall(s))
    total = len(s)
    # Mostly non-word symbols and no real letters/characters => likely garbage.
    return total >= 6 and letters == 0 and _informative_char_count(s) <= 1


# ---------------------------------------------------------------------------
# Unit normalization — collapse notational variants onto a canonical spelling
# so downstream comparison/forecasting see consistent units. Value is unchanged.
# ---------------------------------------------------------------------------
_UNIT_CANON: tuple[tuple[re.Pattern, str], ...] = (
    (re.compile(r"^\s*[％%]\s*$"), "%"),
    (re.compile(r"百万|million|mn|mln", re.I), "million"),
    (re.compile(r"十亿|billion|bn", re.I), "billion"),
    (re.compile(r"人民币.*亿元|亿元|亿"), "亿元"),
    (re.compile(r"人民币.*万元|万元"), "万元"),
    (re.compile(r"美元|usd|us\$", re.I), "USD"),
    (re.compile(r"港[币幣]|hkd|hk\$", re.I), "HKD"),
)


def normalize_unit(unit: str | None) -> str | None:
    """Return a canonical unit spelling (or the original if no rule matches)."""
    if not unit:
        return unit
    u = unit.strip()
    for pat, canon in _UNIT_CANON:
        if pat.search(u):
            return canon
    return u
