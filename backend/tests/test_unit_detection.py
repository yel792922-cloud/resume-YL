"""Unit recognition: title/header inline units, and no fabrication when absent."""
from __future__ import annotations

from app.extraction.value_parser import detect_unit_header, detect_unit_inline


def test_inline_unit_from_header_cell():
    assert detect_unit_inline("2024 (RMB million)")
    assert "百万元" in (detect_unit_inline("（人民币百万元）") or "")
    assert detect_unit_inline("金额 亿元")
    assert "million" in (detect_unit_inline("US$ million") or "").lower()


def test_inline_unit_absent_returns_none():
    # No scale word → do not invent a unit.
    assert detect_unit_inline("2024") is None
    assert detect_unit_inline("Item") is None
    assert detect_unit_inline("") is None
    assert detect_unit_inline(None) is None


def test_page_note_still_detected():
    assert detect_unit_header("单位：人民币（亿元）")
    assert "million" in (detect_unit_header("in millions of USD") or "").lower()
