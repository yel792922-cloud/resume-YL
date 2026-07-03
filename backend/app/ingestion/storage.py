"""Physical storage of uploaded report files."""
from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from app.core.config import get_settings


def new_document_id() -> str:
    return uuid.uuid4().hex


def save_upload(file_obj, original_filename: str, document_id: str | None = None) -> tuple[str, str]:
    """Persist an uploaded file. Returns (document_id, storage_path)."""
    settings = get_settings()
    document_id = document_id or new_document_id()
    safe_name = Path(original_filename).name or "report.pdf"
    dest = settings.uploads_dir / f"{document_id}__{safe_name}"
    with dest.open("wb") as out:
        shutil.copyfileobj(file_obj, out)
    return document_id, str(dest)


def copy_into_store(src_path: str, original_filename: str, document_id: str | None = None) -> tuple[str, str]:
    """Copy an existing file (e.g. the built-in sample) into the store."""
    settings = get_settings()
    document_id = document_id or new_document_id()
    safe_name = Path(original_filename).name or "report.pdf"
    dest = settings.uploads_dir / f"{document_id}__{safe_name}"
    shutil.copyfile(src_path, dest)
    return document_id, str(dest)
