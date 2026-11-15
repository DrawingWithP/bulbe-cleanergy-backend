"""
Configuracao da integracao com o app (variaveis de ambiente / .env).

INTEGRACAO_APP_DB_URL
    Banco do app (o mesmo BULBE_DATABASE_URL do backend).
    - nao definida: usa ../backend/bulbe.db, se o arquivo existir;
    - vazia ou "desligado": integracao desligada.
INTEGRACAO_INTERVALO_SEGUNDOS
    Intervalo da sincronizacao automatica (padrao 30). 0 = so ao subir e pela rota de admin.
INTEGRACAO_APP_API_URL, INTEGRACAO_APP_API_EMAIL, INTEGRACAO_APP_API_SENHA
    API do app e o operador usado para alterar a etapa de ativacao pelo painel
    (padrao: http://127.0.0.1:8000 e o operador de demonstracao do seed do backend).
"""
import os
from dataclasses import dataclass
from pathlib import Path

PASTA_REPOSITORIO = Path(__file__).resolve().parents[3]
CAMINHO_BANCO_APP_PADRAO = PASTA_REPOSITORIO / "backend" / "bulbe.db"

VALORES_DESLIGADO = {"", "desligado", "off", "false", "0", "nao"}

PADRAO_INTERVALO_SEGUNDOS = 30
PADRAO_API_URL = "http://127.0.0.1:8000"
PADRAO_API_EMAIL = "admin@bulbe.com.br"
PADRAO_API_SENHA = "bulbe12345"  # operador de demonstracao do seed do backend (dados ficticios)


@dataclass(frozen=True)
class ConfigIntegracao:
    """Configuracao lida do ambiente no momento do uso."""

    url_banco_app: str | None
    motivo_desligada: str | None
    intervalo_segundos: int
    api_url: str
    api_email: str
    api_senha: str

    @property
    def ativa(self) -> bool:
        return self.url_banco_app is not None


def _inteiro(nome: str, padrao: int, minimo: int, maximo: int) -> int:
    try:
        valor = int(os.getenv(nome) or padrao)
    except ValueError:
        return padrao
    return max(minimo, min(valor, maximo))


def _url_sqlite(caminho: Path) -> str:
    return "sqlite:///" + caminho.resolve().as_posix()


def obter_config() -> ConfigIntegracao:
    """Le as variaveis de ambiente (a cada chamada, para os testes poderem trocar)."""
    bruto = os.environ.get("INTEGRACAO_APP_DB_URL")
    url: str | None
    motivo: str | None = None

    if bruto is None:
        if CAMINHO_BANCO_APP_PADRAO.exists():
            url = _url_sqlite(CAMINHO_BANCO_APP_PADRAO)
        else:
            url = None
            motivo = (
                f"Banco do app nao encontrado em {CAMINHO_BANCO_APP_PADRAO}. "
                "Rode 'alembic upgrade head' na pasta backend/ ou defina INTEGRACAO_APP_DB_URL."
            )
    elif bruto.strip().lower() in VALORES_DESLIGADO:
        url = None
        motivo = "Integracao desligada (INTEGRACAO_APP_DB_URL vazia)."
    else:
        url = bruto.strip()

    return ConfigIntegracao(
        url_banco_app=url,
        motivo_desligada=motivo,
        intervalo_segundos=_inteiro("INTEGRACAO_INTERVALO_SEGUNDOS", PADRAO_INTERVALO_SEGUNDOS, 0, 86_400),
        api_url=(os.getenv("INTEGRACAO_APP_API_URL") or PADRAO_API_URL).rstrip("/"),
        api_email=os.getenv("INTEGRACAO_APP_API_EMAIL") or PADRAO_API_EMAIL,
        api_senha=os.getenv("INTEGRACAO_APP_API_SENHA") or PADRAO_API_SENHA,
    )
