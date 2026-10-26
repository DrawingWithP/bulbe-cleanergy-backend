"""
Configuracoes de seguranca da aplicacao.

Em producao, a chave secreta NUNCA fica no codigo: ela vem de uma
variavel de ambiente. O valor padrao abaixo serve apenas para a aula.
"""

import os

SECRET_KEY: str = os.getenv("BULBE_SECRET_KEY", "troque-esta-chave-em-producao-bulbe-2026")
ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("BULBE_TOKEN_MINUTOS", "30"))