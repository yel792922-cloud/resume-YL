"""OCR path for scanned PDFs (English + Simplified Chinese).

These tests exercise the real Tesseract/Poppler pipeline, so they SKIP cleanly
in environments where the OCR toolchain or a CJK font isn't installed — which
is exactly the graceful-degradation contract the product relies on.
"""
from __future__ import annotations

from pathlib import Path

import pytest

# Candidate CJK fonts (WenQuanYi / Noto) across common distros.
_CJK_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",
    "/usr/share/fonts/truetype/arphic/uming.ttc",
]


def _cjk_font() -> str | None:
    return next((f for f in _CJK_FONT_CANDIDATES if Path(f).exists()), None)


def _ocr_available() -> bool:
    try:
        from app.parsing.ocr import TesseractOcrBackend

        return TesseractOcrBackend().available()
    except Exception:
        return False


def _build_scanned_pdf(dest: Path, font_path: str) -> Path:
    """Render a bilingual income-statement image and save it as an image-only PDF."""
    from PIL import Image, ImageDraw, ImageFont

    big = ImageFont.truetype(font_path, 34)
    reg = ImageFont.truetype(font_path, 28)
    img = Image.new("RGB", (1200, 720), "white")
    d = ImageDraw.Draw(img)
    rows = [
        ("Skylark Technologies 天弘科技  2024 Annual Report", big),
        ("单位：人民币（亿元）  Unit: RMB (100 million)", reg),
        ("营业收入 Revenue                 6,096.9", reg),
        ("毛利 Gross Profit                3,229.2", reg),
        ("毛利率 Gross Margin              53.0%", reg),
        ("净利润 Net Profit                1,946.6", reg),
        ("每股收益 EPS (元)                20.40", reg),
    ]
    y = 40
    for text, f in rows:
        d.text((50, y), text, fill="black", font=f)
        y += 70
    img.save(dest, "PDF", resolution=150.0)
    return dest


pytestmark = pytest.mark.skipif(
    not _ocr_available() or _cjk_font() is None,
    reason="OCR toolchain (tesseract/poppler) or a CJK font is not installed",
)


def test_scanned_pdf_ocr_extracts_bilingual_facts(client, alice, tmp_path):
    pdf = _build_scanned_pdf(tmp_path / "scan.pdf", _cjk_font())
    headers = alice["headers"]

    with pdf.open("rb") as fh:
        doc = client.post(
            "/api/documents/upload",
            headers=headers,
            files={"file": ("scan.pdf", fh, "application/pdf")},
        ).json()

    assert doc["is_scanned"] is True
    assert doc["status"] == "ready"

    facts = client.get(f"/api/documents/{doc['id']}/facts", headers=headers).json()
    by_concept = {f["concept_id"]: f for f in facts if f["concept_id"]}

    # Metrics recovered from the *scanned image* via OCR, matched from both the
    # Chinese and English labels on each row.
    assert "revenue" in by_concept
    assert by_concept["revenue"]["metric_value"] == pytest.approx(6096.9, rel=0.01)
    assert "net_profit" in by_concept
    assert "gross_margin" in by_concept

    # Every OCR-derived fact is still source-traceable (page + bounding box).
    for f in by_concept.values():
        assert f["source"]["page_number"] == 1
        assert f["source"]["bbox"] is not None
        assert f["extraction_method"] in {"text", "table", "derived"}


def test_ocr_disabled_falls_back_gracefully(client, alice, tmp_path, monkeypatch):
    """With OCR disabled, a scanned PDF still ingests (no crash), just no facts."""
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "enable_ocr", False)
    pdf = _build_scanned_pdf(tmp_path / "scan2.pdf", _cjk_font())

    with pdf.open("rb") as fh:
        doc = client.post(
            "/api/documents/upload",
            headers=alice["headers"],
            files={"file": ("scan2.pdf", fh, "application/pdf")},
        ).json()

    assert doc["status"] == "ready"        # graceful, not "failed"
    assert doc["is_scanned"] is True
