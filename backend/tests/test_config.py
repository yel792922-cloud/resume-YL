"""Production configuration safeguards."""
from __future__ import annotations

import pytest

from app.core.config import DEFAULT_DEV_SECRET, get_settings


def test_default_secret_detected():
    assert get_settings().using_default_secret in (True, False)


def test_startup_rejects_default_secret_on_non_sqlite(monkeypatch):
    import app.main as main

    monkeypatch.setattr(main.settings, "secret_key", DEFAULT_DEV_SECRET, raising=False)
    monkeypatch.setattr(main.settings, "database_url", "postgresql+psycopg://u:p@h/db", raising=False)
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        main._check_production_config()


def test_startup_allows_set_secret_on_postgres(monkeypatch):
    import app.main as main

    monkeypatch.setattr(main.settings, "secret_key", "a-real-long-production-secret-key", raising=False)
    monkeypatch.setattr(main.settings, "database_url", "postgresql+psycopg://u:p@h/db", raising=False)
    main._check_production_config()  # should not raise


def test_ocr_dpi_conservative_default():
    # Free-tier safety: default DPI stays modest.
    assert get_settings().ocr_dpi <= 150
