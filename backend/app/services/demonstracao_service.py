"""
Camada de Servico, DemonstracaoService.

Controla o relogio de demonstracao (pular dias) usado na apresentacao:
adiantar o relogio faz cartas do Clube serem liberadas, cupons vencerem e
prazos andarem, sem esperar dias reais. So existe fora de producao.
"""

from datetime import datetime, timezone

from pydantic import BaseModel, Field

from app.core import relogio
from app.db.database import SessionLocal
from app.db.models import RelogioDemonstracaoModel


SEGUNDOS_POR_DIA = 86_400
MAXIMO_DIAS = 365


class ErroDeNegocio(Exception):
    """
    Erro de negocio com formato padronizado:
    code, message e status.
    """

    def __init__(self, code: str, message: str, status: int) -> None:
        self.code = code
        self.message = message
        self.status = status
        super().__init__(message)


class RelogioDemonstracao(BaseModel):
    """Estado do relogio, como a API devolve."""

    modo_demonstracao: bool
    agora: str = Field(..., description="Instante simulado (UTC)")
    hoje: str = Field(..., description="Data simulada (AAAA-MM-DD)")
    dias_adiantados: int = Field(..., ge=0)


class AvancarRelogio(BaseModel):
    """Corpo do POST /v1/demonstracao/relogio/avancar."""

    dias: int = Field(..., ge=1, le=60, description="Quantos dias adiantar")


class DemonstracaoService:
    def __init__(self, session_factory=SessionLocal) -> None:
        self._session_factory = session_factory

    @staticmethod
    def _exigir_demonstracao() -> None:
        if not relogio.modo_demonstracao():
            raise ErroDeNegocio(
                code="DEMONSTRACAO_INDISPONIVEL",
                message=(
                    "O relogio de demonstracao nao existe "
                    "em producao."
                ),
                status=404,
            )

    def estado(self) -> RelogioDemonstracao:
        deslocamento = relogio.deslocamento_segundos()
        agora = relogio.agora()

        return RelogioDemonstracao(
            modo_demonstracao=relogio.modo_demonstracao(),
            agora=relogio.instante_iso(agora),
            hoje=agora.date().isoformat(),
            dias_adiantados=deslocamento // SEGUNDOS_POR_DIA,
        )

    def _gravar(self, segundos: int) -> None:
        with self._session_factory() as session:
            linha = session.get(RelogioDemonstracaoModel, 1)

            if linha is None:
                linha = RelogioDemonstracaoModel(id=1)
                session.add(linha)

            linha.deslocamento_segundos = segundos
            linha.atualizado_em = datetime.now(timezone.utc).replace(
                tzinfo=None
            )
            session.commit()

    def avancar(self, dias: int) -> RelogioDemonstracao:
        """Adianta o relogio em `dias` dias (ate MAXIMO_DIAS no total)."""

        self._exigir_demonstracao()

        total = relogio.deslocamento_segundos() + dias * SEGUNDOS_POR_DIA

        if total > MAXIMO_DIAS * SEGUNDOS_POR_DIA:
            raise ErroDeNegocio(
                code="LIMITE_DEMONSTRACAO",
                message=(
                    f"O relogio de demonstracao vai no maximo "
                    f"{MAXIMO_DIAS} dias a frente. Resete antes."
                ),
                status=422,
            )

        self._gravar(total)
        return self.estado()

    def resetar(self) -> RelogioDemonstracao:
        """Volta o relogio para a data real."""

        self._exigir_demonstracao()
        self._gravar(0)
        return self.estado()


demonstracao_service = DemonstracaoService()
