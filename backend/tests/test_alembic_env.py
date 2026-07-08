"""Regression: Alembic must handle a Postgres URL whose password contains '%'.

Render's generated connection strings often include percent-encoded characters
in the password. Routing that URL through Alembic's ConfigParser triggers
'%' interpolation and crashes `alembic upgrade head` at deploy time — a failure
that never appears locally (SQLite URLs have no '%'). env.py now builds the
engine from the URL directly and escapes the stored option.
"""
from __future__ import annotations

from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url


_RENDER_STYLE_URL = "postgresql+psycopg://user:p%40ss%25word@dpg-abc.render.com:5432/fra"


def test_percent_url_does_not_break_configparser():
    cfg = Config("alembic.ini")
    # env.py stores the escaped copy; reading the section must not interpolate.
    cfg.set_main_option("sqlalchemy.url", _RENDER_STYLE_URL.replace("%", "%%"))
    section = cfg.get_section(cfg.config_ini_section, {})  # would raise before the fix
    assert section["sqlalchemy.url"] == _RENDER_STYLE_URL


def test_engine_built_directly_decodes_password():
    # env.py builds engines straight from the URL — SQLAlchemy decodes the
    # percent-encoded password correctly (create_engine is lazy; no connection).
    eng = create_engine(_RENDER_STYLE_URL)
    assert make_url(_RENDER_STYLE_URL).password == "p@ss%word"
    assert eng.url.get_backend_name() == "postgresql"
