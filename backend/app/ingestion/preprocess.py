"""Pragmatic PDF preprocessing for large / image-heavy uploads.

Two independent safeguards:

1. **Hard size check** (`check_upload_size`) — reject anything over
   ``FRA_MAX_UPLOAD_MB`` before we ever write it to disk, with a clear message.

2. **Optional compression** (`preprocess_pdf`) — for large files, losslessly
   rewrite the PDF with object-stream compression via ``pikepdf`` (safe, does
   *not* touch image resolution, so OCR quality is unaffected). Compression is
   an optimization: if ``pikepdf`` is unavailable, the file isn't actually
   smaller, or anything fails, we keep the original file untouched.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from app.core.config import get_settings


class UploadTooLargeError(Exception):
    """Raised when an upload exceeds the configured hard size limit."""

    def __init__(self, size_bytes: int, limit_bytes: int) -> None:
        self.size_bytes = size_bytes
        self.limit_bytes = limit_bytes
        super().__init__(
            f"File is {size_bytes / 1_048_576:.1f} MB, which exceeds the "
            f"{limit_bytes / 1_048_576:.0f} MB limit."
        )


def check_upload_size(size_bytes: int) -> None:
    settings = get_settings()
    if size_bytes > settings.max_upload_bytes:
        raise UploadTooLargeError(size_bytes, settings.max_upload_bytes)


@dataclass
class PreprocessResult:
    applied: bool
    original_bytes: int
    final_bytes: int
    method: str          # "none" | "pikepdf" | "skipped" | "unavailable" | "error"
    detail: str | None = None


def _pikepdf_compress(path: str) -> bool:
    """Rewrite the PDF in place with stream compression. Returns success."""
    try:
        import pikepdf  # type: ignore
    except Exception:
        return False
    tmp = f"{path}.opt"
    try:
        with pikepdf.open(path) as pdf:
            pdf.save(
                tmp,
                compress_streams=True,
                object_stream_mode=pikepdf.ObjectStreamMode.generate,
                linearize=True,
            )
        # Only adopt the rewrite if it actually got smaller.
        if os.path.getsize(tmp) < os.path.getsize(path):
            os.replace(tmp, path)
            return True
        os.remove(tmp)
        return False
    except Exception:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass
        return False


def preprocess_pdf(path: str) -> PreprocessResult:
    """Optionally shrink a stored PDF. Never raises; falls back to original."""
    settings = get_settings()
    original = os.path.getsize(path)

    if not settings.preprocess_enabled:
        return PreprocessResult(False, original, original, "skipped", "preprocessing disabled")
    if original < settings.preprocess_threshold_mb * 1_048_576:
        return PreprocessResult(False, original, original, "skipped", "below threshold")

    try:
        import pikepdf  # noqa: F401  # type: ignore
    except Exception:
        return PreprocessResult(False, original, original, "unavailable", "pikepdf not installed")

    if _pikepdf_compress(path):
        final = os.path.getsize(path)
        return PreprocessResult(True, original, final, "pikepdf")
    return PreprocessResult(False, original, original, "error", "no size reduction / failed")
