"""
Tres pecas de conexao com o banco, criadas uma vez
e usadas por todos os repositorios.

- engine: conexao principal com o banco, criada a partir do DATABASE_URL.
- SessionLocal: fabrica de sessoes. Cada operacao do repositorio abre a sua.
- Base: classe-mae dos modelos ORM. Base.metadata conhece todas as tabelas.
"""

from sqlalchemy import (
    create_engine,
    event,
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import (
    DeclarativeBase,
    sessionmaker,
)

from app.core.config import DATABASE_URL


_eh_sqlite = DATABASE_URL.startswith("sqlite")


engine: Engine = create_engine(
    DATABASE_URL,
    # O SQLite, por padrao, restringe a conexao
    # a thread que a criou.
    # O FastAPI pode executar requisicoes em threads
    # diferentes, por isso essa verificacao e desabilitada.
    connect_args=(
        {"check_same_thread": False}
        if _eh_sqlite
        else {}
    ),
)


if _eh_sqlite:

    @event.listens_for(engine, "connect")
    def _ativar_chaves_estrangeiras(
        conexao_dbapi,
        _registro,
    ) -> None:
        """
        Ativa o suporte a FOREIGN KEY no SQLite.

        Isso tambem permite que regras como
        ON DELETE CASCADE e ON DELETE SET NULL
        funcionem corretamente.
        """

        cursor = conexao_dbapi.cursor()

        try:
            cursor.execute(
                "PRAGMA foreign_keys=ON"
            )
        finally:
            cursor.close()


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """
    Classe-mae de todos os modelos ORM do projeto.
    """

    pass
