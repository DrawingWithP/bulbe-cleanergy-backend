"""
Relogio da aplicacao.

Todas as regras que dependem de "hoje" (Clube Bulbe, validade de cupons,
previsao da ativacao, datas de cadastro) usam agora() / hoje() deste modulo
em vez de datetime.now().

Fora de producao, o relogio pode ser adiantado para a demonstracao
(POST /v1/demonstracao/relogio/avancar): o deslocamento fica gravado na
tabela relogio_demonstracao e vale para todos os processos que usam o banco.
Em producao (BULBE_AMBIENTE=producao) o deslocamento e sempre zero.

Exceção proposital: a validade dos tokens JWT usa a hora real
(app/core/security.py), porque o PyJWT confere a expiracao com o relogio
do sistema.
"""

from datetime import date, datetime, timedelta, timezone

from app.core import config


FORMATO_INSTANTE = "%Y-%m-%dT%H:%M:%SZ"


def modo_demonstracao() -> bool:
    """O relogio so pode ser adiantado fora de producao."""

    return config.AMBIENTE != "producao"


def deslocamento_segundos() -> int:
    """Deslocamento gravado no banco (0 se nao houver ou em producao)."""

    if not modo_demonstracao():
        return 0

    try:
        from app.db.database import SessionLocal
        from app.db.models import RelogioDemonstracaoModel

        with SessionLocal() as session:
            linha = session.get(RelogioDemonstracaoModel, 1)
            return int(linha.deslocamento_segundos) if linha else 0
    except Exception:  # tabela ainda nao criada (banco sem migration)
        return 0


def agora() -> datetime:
    """Instante atual em UTC, ja com o deslocamento da demonstracao."""

    return datetime.now(timezone.utc) + timedelta(
        seconds=deslocamento_segundos()
    )


def hoje() -> date:
    """Data atual (UTC) com o deslocamento da demonstracao."""

    return agora().date()


def instante_iso(momento: datetime | None = None) -> str:
    """Instante no formato usado pela API (AAAA-MM-DDTHH:MM:SSZ)."""

    return (momento or agora()).strftime(FORMATO_INSTANTE)


def ler_instante(texto: str) -> datetime:
    """Converte 'AAAA-MM-DDTHH:MM:SSZ' (ou ISO com fuso) em datetime UTC."""

    valor = datetime.fromisoformat(texto.replace("Z", "+00:00"))

    if valor.tzinfo is None:
        valor = valor.replace(tzinfo=timezone.utc)

    return valor.astimezone(timezone.utc)
