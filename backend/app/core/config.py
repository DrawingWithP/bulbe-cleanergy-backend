"""
Configuracoes da aplicacao (seguranca e banco de dados).

Em producao, a chave secreta NUNCA fica no codigo: ela vem de uma
variavel de ambiente. O valor padrao abaixo serve apenas para a aula.
"""

import os

SECRET_KEY: str = os.getenv("BULBE_SECRET_KEY", "troque-esta-chave-em-producao-bulbe-2026")
ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("BULBE_TOKEN_MINUTOS", "30"))

# Banco de dados. Padrao: SQLite em um arquivo local (bulbe.db, fora do Git).
# PostgreSQL:  postgresql+psycopg://bulbe:bulbe@localhost:5432/bulbe
DATABASE_URL: str = os.getenv("BULBE_DATABASE_URL", "sqlite:///./bulbe.db")
