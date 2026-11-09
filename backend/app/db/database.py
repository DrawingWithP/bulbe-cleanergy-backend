"""
Tres pecas de conexao com o banco, criadas uma vez e usadas por todos os repositorios.

- engine: o "cano" ate o banco. Um so por aplicacao, criado a partir do DATABASE_URL.
- SessionLocal: fabrica de sessoes. Cada operacao do repositorio abre a sua.
- Base: classe-mae dos modelos. Base.metadata conhece todas as tabelas.
"""

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import DATABASE_URL

_eh_sqlite = DATABASE_URL.startswith("sqlite")

engine: Engine = create_engine(
    DATABASE_URL,
    # O SQLite, por padrao, so aceita a conexao na thread que a criou.
    # O FastAPI atende requisicoes em threads diferentes, por isso liberamos.
    connect_args={"check_same_thread": False} if _eh_sqlite else {},
)

if _eh_sqlite:

    @event.listens_for(engine, "connect")
    def _ativar_chaves_estrangeiras(conexao_dbapi, _registro) -> None:
        """O SQLite so respeita FOREIGN KEY (e ON DELETE CASCADE) com este PRAGMA ligado."""
        cursor = conexao_dbapi.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False)


class Base(DeclarativeBase):
    """Classe-mae de todos os modelos ORM do projeto."""
