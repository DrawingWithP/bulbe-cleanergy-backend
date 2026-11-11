"""
Configuracoes da aplicacao:
seguranca, autenticacao e banco de dados.

Em producao, dados sensiveis como a chave secreta
devem ser fornecidos por variaveis de ambiente.
"""

import os


SECRET_KEY: str = os.getenv(
    "BULBE_SECRET_KEY",
    "troque-esta-chave-em-producao-bulbe-2026",
)

ALGORITHM: str = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
    os.getenv(
        "BULBE_TOKEN_MINUTOS",
        "30",
    )
)

# Banco de dados.
#
# Padrao:
# SQLite utilizando o arquivo local bulbe.db.
#
# Exemplo PostgreSQL:
# postgresql+psycopg://bulbe:bulbe@localhost:5432/bulbe
DATABASE_URL: str = os.getenv(
    "BULBE_DATABASE_URL",
    "sqlite:///./bulbe.db",
)
