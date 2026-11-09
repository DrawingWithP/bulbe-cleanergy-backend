"""
Ambiente do Alembic.

Usa o DATABASE_URL e o Base.metadata do projeto, para que:
- "alembic revision --autogenerate" compare os modelos (app/db/models.py) com o banco;
- "alembic upgrade head" aplique as migrations no mesmo banco que a API usa.
"""

from logging.config import fileConfig

from alembic import context

from app.core.config import DATABASE_URL
from app.db import models  # noqa: F401  (registra todas as tabelas no Base.metadata)
from app.db.database import Base, engine

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# O endereco do banco vem sempre do projeto (variavel BULBE_DATABASE_URL),
# nunca fixo no alembic.ini.
config.set_main_option("sqlalchemy.url", DATABASE_URL)

target_metadata = Base.metadata

# SQLite nao altera colunas com ALTER TABLE; o "batch mode" recria a tabela.
_render_as_batch = DATABASE_URL.startswith("sqlite")


def run_migrations_offline() -> None:
    """Gera o SQL sem conectar no banco (alembic upgrade head --sql)."""
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=_render_as_batch,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Conecta no banco usando o mesmo engine da aplicacao."""
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=_render_as_batch,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
