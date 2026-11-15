"""
Configuracoes da aplicacao:
seguranca, autenticacao e banco de dados.

Os valores vem de variaveis de ambiente. Se existir um arquivo
backend/.env (copie de .env.example), ele e lido ao iniciar; variaveis
ja definidas no ambiente tem prioridade sobre o arquivo.

Em producao (BULBE_AMBIENTE=producao) a chave secreta e obrigatoria.
"""

import logging
import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv(
        Path(__file__).resolve().parents[2] / ".env",
        override=False,
    )
except ImportError:  # pragma: no cover - python-dotenv e opcional
    pass


logger = logging.getLogger(__name__)

AMBIENTE: str = os.getenv(
    "BULBE_AMBIENTE",
    "desenvolvimento",
).strip().lower()

_CHAVE_DESENVOLVIMENTO = "chave-somente-para-desenvolvimento-local-bulbe"

SECRET_KEY: str = os.getenv("BULBE_SECRET_KEY") or ""

if not SECRET_KEY:
    if AMBIENTE == "producao":
        raise RuntimeError(
            "BULBE_SECRET_KEY e obrigatoria quando "
            "BULBE_AMBIENTE=producao."
        )

    logger.warning(
        "BULBE_SECRET_KEY nao definida: usando uma chave fixa "
        "de desenvolvimento. Nao use assim em producao."
    )
    SECRET_KEY = _CHAVE_DESENVOLVIMENTO

ALGORITHM: str = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
    os.getenv("BULBE_TOKEN_MINUTOS") or "30"
)

# Banco de dados.
#
# Padrao:
# SQLite utilizando o arquivo local bulbe.db.
#
# Exemplo PostgreSQL:
# postgresql+psycopg://bulbe:bulbe@localhost:5432/bulbe
# Variavel vazia (como no .env.example) tambem usa o padrao.
DATABASE_URL: str = (
    os.getenv("BULBE_DATABASE_URL")
    or "sqlite:///./bulbe.db"
)
