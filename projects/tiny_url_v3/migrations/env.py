from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.config import get_settings
from app.database_models import Base


config = context.config


if config.config_file_name is not None:
    fileConfig(config.config_file_name)


settings = get_settings()

# Alembic uses ConfigParser internally. Escaping "%"
# avoids interpolation problems in URLs containing percent signs.
config.set_main_option(
    "sqlalchemy.url",
    settings.database_url.replace("%", "%%"),
)

# Base.metadata contains the intended application schema:
    # Base.metadata
    # └── short_urls
    #     ├── columns
    #     ├── primary key
    #     ├── unique constraint
    #     └── check constraint
target_metadata = Base.metadata

is_sqlite = settings.database_url.startswith(
    "sqlite"
)


def run_migrations_offline() -> None:
    url = config.get_main_option(
        "sqlalchemy.url"
    )

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={
            "paramstyle": "named",
        },
        compare_type=True,
        render_as_batch=is_sqlite,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(
        config.config_ini_section,
        {},
    )

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            render_as_batch=is_sqlite,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()