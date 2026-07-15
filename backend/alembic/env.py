"""Alembic environment configuration — reads database URL from AuraSaaS settings."""

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from sqlalchemy import create_engine

from alembic import context

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# --- AuraSaaS: import all models so autogenerate can detect them ---
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.database import Base
from app.core.config import get_settings
import app.models.models  # noqa: F401 — ensures all models are registered

settings = get_settings()
target_metadata = Base.metadata

# Override sqlalchemy.url from project settings
config.set_main_option("sqlalchemy.url", settings.database_url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = create_engine(settings.database_url)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
