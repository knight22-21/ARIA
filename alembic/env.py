"""Alembic migration environment (async).

Pulls the DB URL from app settings and imports the model metadata so that
``alembic revision --autogenerate`` sees every ORM table.
"""

import asyncio
from logging.config import fileConfig

from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlalchemy.pool import NullPool

# Importing the models package registers every ORM table on Base.metadata,
# which `--autogenerate` relies on. (Concrete models land in Phase 1.)
import app.models  # noqa: F401
from alembic import context
from app.core.config import settings
from app.core.db import Base

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def render_item(type_, obj, autogen_context):  # noqa: ANN001
    """Render the app-layer EncryptedString column as plain sa.String in migrations.

    Encryption is an application concern; at the DB level the column is a VARCHAR,
    so migrations must not import app code.
    """
    from app.core.crypto import EncryptedString

    if type_ == "type" and isinstance(obj, EncryptedString):
        length = getattr(obj.impl, "length", None)
        return f"sa.String(length={length})" if length else "sa.String()"
    return False


def do_run_migrations(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        render_item=render_item,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_async_migrations())
