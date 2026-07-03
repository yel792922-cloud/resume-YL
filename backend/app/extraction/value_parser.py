"""Parse printed financial numbers (CN & EN) into structured values.

Handles: thousands separators, parenthesized / bracketed negatives, percentages,
per-share amounts, and both Chinese (亿 / 万 / 万亿) and English
(thousand / million / billion) scale words. The *magnitude as printed* is
preserved; the detected scale/unit is returned alongside so nothing is silently
rescaled and the original snippet stays verifiable.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# A number possibly wrapped in parens/brackets for negatives, with separators.
_NUMBER_RE = re.compile(
    r"""
    (?P<neg_open>[(（\[【])?\s*
    (?P<sign>[-+−])?\s*
    (?P<currency>[¥$€£])?\s*
    (?P<num>\d{1,3}(?:[,，]\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)
    \s*(?P<pct>%|％)?
    \s*(?P<scale_zh>万亿|亿|万|千|百万)?
    \s*(?P<neg_close>[)）\]】])?
    """,
    re.VERBOSE,
)

_SCALE_ZH = {"万亿": 1e12, "亿": 1e8, "万": 1e4, "千": 1e3, "百万": 1e6}
_SCALE_EN = {"thousand": 1e3, "million": 1e6, "billion": 1e9, "trillion": 1e12}
_CURRENCY = {"¥": "CNY", "$": "USD", "€": "EUR", "£": "GBP"}

_UNIT_HEADER_ZH_RE = re.compile(r"单位\s*[:：]?\s*([^\s，,；;、]+)")


@dataclass
class ParsedValue:
    value: float                  # magnitude as printed (sign applied)
    unit: str | None              # e.g. "%", "亿元", "million", "CNY"
    is_percent: bool
    raw: str                      # the exact matched substring


def _to_float(num: str, sign: str | None, negated: bool) -> float:
    val = float(num.replace(",", "").replace("，", ""))
    if sign in ("-", "−") or negated:
        val = -val
    return val


def parse_number(text: str, unit_hint: str | None = None) -> ParsedValue | None:
    """Parse the first numeric value in ``text``. Returns None if none found."""
    if text is None:
        return None
    s = str(text).strip()
    if not s:
        return None

    m = _NUMBER_RE.search(s)
    if not m or not m.group("num"):
        return None

    negated = bool(m.group("neg_open") and m.group("neg_close"))
    value = _to_float(m.group("num"), m.group("sign"), negated)

    is_percent = bool(m.group("pct"))
    unit: str | None = None
    if is_percent:
        unit = "%"
    else:
        scale = m.group("scale_zh")
        # English scale word following the number, e.g. "12.3 million".
        tail = s[m.end():].lstrip()
        en_scale = next((w for w in _SCALE_EN if tail.lower().startswith(w)), None)
        currency = _CURRENCY.get(m.group("currency") or "")
        if scale:
            unit = f"{scale}"
        elif en_scale:
            unit = en_scale
        elif currency:
            unit = currency
        elif unit_hint:
            unit = unit_hint

    return ParsedValue(value=value, unit=unit, is_percent=is_percent, raw=m.group(0).strip())


def looks_numeric(text: str | None) -> bool:
    if not text:
        return False
    return bool(re.search(r"\d", str(text)))


def detect_unit_header(text: str) -> str | None:
    """Pull a table/page unit hint like '单位：人民币（亿元）' or 'in millions'."""
    if not text:
        return None
    m = _UNIT_HEADER_ZH_RE.search(text)
    if m:
        body = m.group(1).strip()
        if body:
            return body[:24]
    # English "in millions / in thousands (USD)" style.
    m2 = re.search(r"in\s+(thousands|millions|billions)(?:\s+of\s+([A-Za-z]{3}))?", text, re.IGNORECASE)
    if m2:
        scale = m2.group(1).lower()
        cur = (m2.group(2) or "").upper()
        return f"{scale}{(' ' + cur) if cur else ''}"
    return None
