"""Regression: the database URL must be handled safely for passwords containing
URL-sensitive characters (%, @, :, /, ?, #, &, spaces).

All of these are exercised through the *single* source of truth
(`config.coerce_db_url` / `Settings.sqlalchemy_url`), which both the app runtime
(`app.core.db`) and Alembic (`alembic/env.py`) consume — so one safe path can't
drift from another.
"""
from __future__ import annotations

import subprocess
import sys

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url

from app.core.config import Settings, coerce_db_url

# A password exercising every URL-sensitive character the task calls out,
# percent-encoded exactly as a valid connection string would carry it.
_ENCODED_PW = "%25%40%3A%2F%3F%23%26%20end"          # -> "%@:/?#& end"
_DECODED_PW = "%@:/?#& end"
_RENDER_URL = f"postgres://dbuser:{_ENCODED_PW}@dpg-abc.oregon-postgres.render.com:5432/fra"


def test_coerce_decodes_special_chars_and_upgrades_driver():
    url = coerce_db_url(_RENDER_URL)
    assert url.password == _DECODED_PW          # every special char decoded once
    assert url.drivername == "postgresql+psycopg"  # postgres:// upgraded to psycopg 3
    assert url.host == "dpg-abc.oregon-postgres.render.com"
    assert url.database == "fra"


def test_each_sensitive_char_survives_round_trip():
    for enc, dec in [("%25", "%"), ("%40", "@"), ("%3A", ":"), ("%2F", "/"),
                     ("%3F", "?"), ("%23", "#"), ("%26", "&"), ("%20", " ")]:
        url = coerce_db_url(f"postgresql://u:aa{enc}bb@h:5432/d")
        assert url.password == f"aa{dec}bb", f"char {dec!r} not handled"


def test_settings_exposes_safe_url_object_and_string():
    s = Settings(database_url=_RENDER_URL, secret_key="x" * 40)
    # The canonical URL object carries the real (decoded) password...
    assert s.sqlalchemy_url.password == _DECODED_PW
    assert s.is_sqlite is False and s.db_backend == "postgresql"
    # ...and the stored string is a valid, re-encoded URL that round-trips.
    assert make_url(s.database_url).password == _DECODED_PW


def test_create_engine_accepts_the_url_without_crashing():
    # This is exactly what app.core.db and alembic env.py do (engine is lazy —
    # no connection attempted). A parse/format bug would raise here.
    eng = create_engine(coerce_db_url(_RENDER_URL))
    assert eng.url.password == _DECODED_PW
    assert eng.url.get_backend_name() == "postgresql"


def test_sqlite_default_is_unaffected():
    s = Settings(database_url="sqlite:///./local.db")
    assert s.is_sqlite is True and s.db_backend == "sqlite"


def test_alembic_startup_consumes_special_char_url(tmp_path):
    """`alembic upgrade head --sql` (offline; the migration-startup path) must
    consume a '%'-laden URL without crashing — the original deploy failure."""
    env = {
        "PATH": __import__("os").environ["PATH"],
        "DATABASE_URL": _RENDER_URL,
        "FRA_SECRET_KEY": "x" * 40,
    }
    proc = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head", "--sql"],
        capture_output=True, text=True, env=env,
    )
    assert proc.returncode == 0, proc.stderr
    assert "interpolation" not in proc.stderr.lower()
    assert "ADD COLUMN is_guest" in proc.stdout   # migrations actually rendered
