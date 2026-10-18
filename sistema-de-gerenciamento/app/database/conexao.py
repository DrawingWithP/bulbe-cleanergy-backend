"""
Camada de Persistencia, conexao com o banco de dados ficticio (SQLAlchemy 2).

Por padrao usa um arquivo SQLite em app/database/bulbe_ficticio.db (caminho absoluto,
calculado a partir deste arquivo, entao funciona de qualquer diretorio de trabalho).
Para usar outro banco, defina a variavel de ambiente BULBE_DB_URL.
"""
import logging
import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import URL, create_engine, event, func, select
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

try:  # python-dotenv e opcional: se existir, le o .env antes de ler BULBE_DB_URL
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover
    pass

logger = logging.getLogger(__name__)

CAMINHO_BANCO_PADRAO: Path = (Path(__file__).parent / "bulbe_ficticio.db").resolve()

# URL.create evita problemas de parsing com espacos e acentos no caminho (ex.: "Área de Trabalho").
BULBE_DB_URL: str | URL = os.getenv("BULBE_DB_URL") or URL.create(
    "sqlite", database=str(CAMINHO_BANCO_PADRAO)
)


class Base(DeclarativeBase):
    """Classe base de todos os modelos ORM."""


def _eh_sqlite(url: str | URL) -> bool:
    return str(url).startswith("sqlite")


engine = create_engine(
    BULBE_DB_URL,
    connect_args={"check_same_thread": False} if _eh_sqlite(BULBE_DB_URL) else {},
)

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


if engine.dialect.name == "sqlite":

    @event.listens_for(engine, "connect")
    def _ativar_chaves_estrangeiras(conexao_dbapi, _registro) -> None:  # type: ignore[no-untyped-def]
        """O SQLite so respeita FOREIGN KEY com este PRAGMA ligado em cada conexao."""
        cursor = conexao_dbapi.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


@contextmanager
def obter_sessao() -> Iterator[Session]:
    """Abre uma sessao; commita se tudo der certo, faz rollback em erro e sempre fecha."""
    sessao = SessionLocal()
    try:
        yield sessao
        sessao.commit()
    except Exception:
        sessao.rollback()
        raise
    finally:
        sessao.close()


def _apagar_tabelas() -> None:
    """Apaga todas as tabelas (usado por recriar=True)."""
    from app.database import modelos  # noqa: F401  (registra as tabelas no Base.metadata)

    with engine.connect() as conexao:
        if engine.dialect.name == "sqlite":
            # cartas <-> cupons tem FK circular; desligar as FKs evita erro no DROP.
            conexao.exec_driver_sql("PRAGMA foreign_keys=OFF")
        Base.metadata.drop_all(bind=conexao)
        conexao.commit()
        if engine.dialect.name == "sqlite":
            conexao.exec_driver_sql("PRAGMA foreign_keys=ON")


def inicializar_banco(recriar: bool = False) -> None:
    """
    Cria as tabelas que ainda nao existem. Se recriar=True, apaga tudo antes.

    O seed so roda com recriar=True ou quando o banco esta realmente vazio
    (clientes E funcionarios E usinas E parceiros sem nenhuma linha). Num estado parcial
    (ex.: clientes vazio mas funcionarios preenchido) o seed NAO roda, para nao levantar
    IntegrityError nas colunas unicas; apenas registra um aviso sugerindo recriar o banco.
    """
    from app.database import modelos  # noqa: F401  (registra as tabelas no Base.metadata)
    from app.database.modelos import Cliente, Funcionario, Parceiro, Usina
    from app.database.seed import popular_banco

    if recriar:
        _apagar_tabelas()
    Base.metadata.create_all(bind=engine)

    with obter_sessao() as sessao:
        contagens = {
            modelo.__tablename__: sessao.scalar(select(func.count()).select_from(modelo)) or 0
            for modelo in (Cliente, Funcionario, Usina, Parceiro)
        }
        if recriar or not any(contagens.values()):
            popular_banco(sessao)
        elif contagens["clientes"] == 0 or contagens["funcionarios"] == 0:
            logger.warning(
                "Banco ficticio em estado parcial %s; seed nao executado. "
                "Recrie com: python -m app.database.seed",
                contagens,
            )
