"""Upload size limits and PDF preprocessing safeguards."""
from __future__ import annotations

import pytest

from app.core.config import get_settings
from app.ingestion.preprocess import (
    UploadTooLargeError,
    check_upload_size,
    preprocess_pdf,
)


def test_check_upload_size_enforced():
    settings = get_settings()
    check_upload_size(1024)  # small: ok
    with pytest.raises(UploadTooLargeError):
        check_upload_size(settings.max_upload_bytes + 1)


def test_preprocess_never_raises_and_falls_back(tmp_path):
    # A tiny non-image PDF: preprocessing should skip (below threshold), not fail.
    from app.sample.sample_report import build_sample_pdf

    pdf = build_sample_pdf(tmp_path / "s.pdf")
    result = preprocess_pdf(str(pdf))
    assert result.method in {"skipped", "pikepdf", "unavailable", "error", "none"}
    assert result.final_bytes > 0  # file still intact


def test_oversized_upload_returns_413(client, alice, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "max_upload_mb", 0)  # force everything oversized
    res = client.post(
        "/api/documents/upload",
        headers=alice["headers"],
        files={"file": ("big.pdf", b"%PDF-1.4 fake content", "application/pdf")},
    )
    assert res.status_code == 413
    assert "exceeds" in res.json()["detail"].lower()
