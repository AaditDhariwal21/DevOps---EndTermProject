from logging.config import fileConfig

from sqlalchemy import create_engine, pool, text

from alembic import context
from app import models  # noqa: F401 - registers tables on Base.metadata
from app.config import get_settings
from app.database import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Arbitrary constant: every backend replica runs `alembic upgrade head` on start,
# and this Postgres advisory lock makes them take turns instead of racing.
MIGRATION_LOCK_ID = 727274


def run_migrations_offline() -> None:
    context.configure(
        url=get_settings().sqlalchemy_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(get_settings().sqlalchemy_url, poolclass=pool.NullPool)
    with engine.connect() as connection:
        is_postgres = connection.dialect.name == "postgresql"
        if is_postgres:
            connection.execute(text("SELECT pg_advisory_lock(:id)"), {"id": MIGRATION_LOCK_ID})
            connection.commit()
        try:
            context.configure(connection=connection, target_metadata=target_metadata)
            with context.begin_transaction():
                context.run_migrations()
            connection.commit()
        finally:
            if is_postgres:
                connection.execute(
                    text("SELECT pg_advisory_unlock(:id)"), {"id": MIGRATION_LOCK_ID}
                )
                connection.commit()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
