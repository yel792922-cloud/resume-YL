"""Extract metrics from narrative text — a lower-trust fallback to tables.

Scans line by line for a concept label followed by a number, e.g.
"营业收入 6,096.9 亿元" or "Revenue was $609,693 million". Facts get a bbox by
locating the snippet among the page's positioned words.
"""
from __future__ import annotations

import re

from app.extraction.base import FactDraft
from app.extraction.value_parser import detect_unit_header, parse_number
from app.normalization.dictionary import TermMatcher, detect_language
from app.sourcemap.highlight import locate_snippet

_LINE_SPLIT = re.compile(r"[\n\r]+")


def extract_from_text(
    page_number: int,
    page_text: str,
    words: list[dict],
    matcher: TermMatcher,
    already_found: set[str],
) -> list[FactDraft]:
    """Extract concepts *not* in ``already_found`` from the page's prose."""
    drafts: list[FactDraft] = []
    unit_hint = detect_unit_header(page_text)

    for line in _LINE_SPLIT.split(page_text):
        line = line.strip()
        if not line or not re.search(r"\d", line):
            continue
        hit = matcher.find_in(line)
        if hit is None or hit.concept.id in already_found:
            continue

        # Parse the number that follows the matched alias.
        idx = line.lower().find(hit.matched_alias.lower())
        tail = line[idx + len(hit.matched_alias):] if idx >= 0 else line
        this_hint = "%" if hit.concept.unit_hint == "percent" else unit_hint
        parsed = parse_number(tail, unit_hint=this_hint) or parse_number(line, unit_hint=this_hint)
        if parsed is None:
            continue

        bbox = locate_snippet(words, line[:60]) or locate_snippet(words, hit.matched_alias)
        drafts.append(
            FactDraft(
                category=hit.concept.category,
                concept_id=hit.concept.id,
                metric_name=hit.concept.canonical_en,
                metric_label=hit.concept.canonical_zh,
                raw_label=hit.matched_alias,
                language=detect_language(line),
                metric_value=parsed.value,
                value_text=parsed.raw,
                unit=parsed.unit,
                source_page_number=page_number,
                report_section="Narrative",
                source_text_snippet=line[:400],
                source_bbox=bbox,
                confidence_score=0.6,
                extraction_method="text",
            )
        )
        already_found.add(hit.concept.id)
    return drafts
