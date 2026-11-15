from logging.config import fileConfig

from alembic import context
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, pool, text
from sqlalchemy.engine import Connection, make_url
from sqlalchemy.ext.asyncio import async_engine_from_config

from sfi_api.config import get_settings
from sfi_api.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata
SQLITE_BASELINE_REVISION = "0013_security_events"


def database_url() -> str:
    value = get_settings().database_url
    if not value:
        raise RuntimeError("SFI_DATABASE_URL ou SFI_DATA_DIR deve estar configurada para migrações.")
    url = make_url(value)
    if url.drivername in {"postgres", "postgresql"}:
        url = url.set(drivername="postgresql+asyncpg")
    query = dict(url.query)
    sslmode = query.pop("sslmode", None)
    if sslmode and "ssl" not in query:
        query["ssl"] = sslmode
    query.pop("channel_binding", None)
    return url.set(query=query).render_as_string(hide_password=False)


def run_migrations_offline() -> None:
    context.configure(
        url=database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


def bootstrap_empty_sqlite_database(connection: Connection) -> None:
    table_names = set(inspect(connection).get_table_names())
    application_tables = table_names - {"alembic_version"}
    has_version_table = "alembic_version" in table_names

    if application_tables and not has_version_table:
        raise RuntimeError(
            "SQLite existente sem alembic_version. A migração automática foi interrompida "
            "para evitar assumir uma versão de schema desconhecida."
        )

    if has_version_table:
        version = connection.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar_one_or_none()
        if version:
            script = ScriptDirectory.from_config(config)
            revision = script.get_revision(version)
            if revision is None:
                raise RuntimeError(
                    f"Revisão SQLite desconhecida ({version!r}); migração automática interrompida."
                )

            baseline = script.get_revision(SQLITE_BASELINE_REVISION)
            current = revision
            while current is not None and current.revision != SQLITE_BASELINE_REVISION:
                down_revision = current.down_revision
                if not isinstance(down_revision, str):
                    current = None
                    break
                current = script.get_revision(down_revision)

            if baseline is None or current is None:
                raise RuntimeError(
                    f"Schema SQLite legado ({version!r}) não deriva da baseline local suportada."
                )
            return

        if application_tables:
            raise RuntimeError(
                "SQLite contém tabelas, mas alembic_version está vazio. "
                "A migração automática foi interrompida para preservar os dados."
            )

    Base.metadata.create_all(connection)
    head_revision = ScriptDirectory.from_config(config).get_current_head()
    if not head_revision:
        raise RuntimeError("Não foi possível determinar a revisão atual das migrações.")

    connection.execute(
        text(
            "CREATE TABLE IF NOT EXISTS alembic_version "
            "(version_num VARCHAR(32) NOT NULL PRIMARY KEY)"
        )
    )
    connection.execute(
        text("INSERT INTO alembic_version (version_num) VALUES (:revision)"),
        {"revision": head_revision},
    )

async def run_migrations_online() -> None:
    section = config.get_section(config.config_ini_section, {})
    section["sqlalchemy.url"] = database_url()
    connectable = async_engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        if connection.dialect.name == "sqlite":
            await connection.run_sync(bootstrap_empty_sqlite_database)
            await connection.commit()
            await connection.run_sync(do_run_migrations)
            await connection.commit()
        else:
            await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    import asyncio

    asyncio.run(run_migrations_online())
