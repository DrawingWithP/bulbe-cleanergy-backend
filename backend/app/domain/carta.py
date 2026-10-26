"""
Camada de Domínio, entidade Carta e Clube Bulbe (US-18, US-19, US-20 e US-21).
"""
from enum import Enum
from pydantic import BaseModel, Field

from app.domain.cupom import Cupom


class SituacaoCarta(str, Enum):
    disponivel = "disponivel"
    aberta = "aberta"
    bloqueada = "bloqueada"
    expirada = "expirada"


class TipoCarta(str, Enum):
    normal = "normal"
    especial = "especial"


class Carta(BaseModel):
    id: str
    cliente_id: str
    semana: int
    tipo: TipoCarta = TipoCarta.normal
    situacao: SituacaoCarta = SituacaoCarta.disponivel
    disponivel_em: str
    aberta_em: str | None = None
    cupom_id: str | None = None

    class Config:
        from_attributes = True


class ProximaCartaInfo(BaseModel):
    carta_id: str
    disponivel_em: str
    dias_restantes: int = 0


class ClubeSituacaoResponse(BaseModel):
    """Situação geral do cliente no Clube Bulbe (US-18)."""
    cliente_id: str
    semanas_sequencia: int = 0
    meta_sequencia: int = 5
    carta_disponivel: bool = False
    bonus_especial_pendente: bool = False
    proxima_carta: ProximaCartaInfo | None = None
    intervalo_dias: int = 7


class CartaListaPaginada(BaseModel):
    data: list[Carta]
    page: int
    total: int


class AberturaCartaResponse(BaseModel):
    """Resposta após abrir a carta e resgatar o cupom (US-21)."""
    carta_id: str
    semanas_sequencia: int
    meta_sequencia: int = 5
    cupom: Cupom
    proxima_carta_em: str
