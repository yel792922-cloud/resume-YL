"""Alembic environment — reads the DB URL from app settings (env-driven)."""
from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from app.core.config import get_settings
from app.core.db import Base

# Import models so their tables are registered on Base.metadata.
from app.models import document, fact, snapshot, user  # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# The live DB URL. We build engines from this string *directly* (below) instead
# of routing it through Alembic's ConfigParser: a Postgres password containing
# '%' (common in Render's generated connection strings) would otherwise trigger
# ConfigParser interpolation and crash `alembic upgrade head` at deploy time.
DB_URL = get_settings().database_url
# Escaped copy so any *internal* Alembic read of this option can't interpolate.
config.set_main_option("sqlalchemy.url", DB_URL.replace("%", "%%"))

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=DB_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(DB_URL, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
