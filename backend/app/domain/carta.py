"""
Camada de Domínio, entidade Carta e Clube Bulbe
(US-18, US-19, US-20 e US-21).
"""

from enum import Enum

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

from app.domain.cupom import Cupom


META_SEQUENCIA = 5
INTERVALO_CARTAS_DIAS = 7


class SituacaoCarta(str, Enum):
    disponivel = "disponivel"
    aberta = "aberta"
    bloqueada = "bloqueada"
    expirada = "expirada"


class TipoCarta(str, Enum):
    normal = "normal"
    especial = "especial"


class Carta(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: str
    cliente_id: str

    semana: int = Field(
        ...,
        ge=1,
    )

    tipo: TipoCarta = TipoCarta.normal

    situacao: SituacaoCarta = (
        SituacaoCarta.disponivel
    )

    disponivel_em: str
    aberta_em: str | None = None
    cupom_id: str | None = None


class ProximaCartaInfo(BaseModel):
    carta_id: str
    disponivel_em: str

    dias_restantes: int = Field(
        default=0,
        ge=0,
    )


class ClubeSituacaoResponse(BaseModel):
    """
    Situação geral do cliente no Clube Bulbe
    (US-18).
    """

    cliente_id: str

    semanas_sequencia: int = Field(
        default=0,
        ge=0,
    )

    meta_sequencia: int = Field(
        default=META_SEQUENCIA,
        ge=1,
    )

    carta_disponivel: bool = False

    bonus_especial_pendente: bool = False

    proxima_carta: ProximaCartaInfo | None = None

    intervalo_dias: int = Field(
        default=INTERVALO_CARTAS_DIAS,
        ge=1,
    )


class CartaListaPaginada(BaseModel):
    data: list[Carta]

    page: int = Field(
        ...,
        ge=1,
    )

    total: int = Field(
        ...,
        ge=0,
    )


class AberturaCartaResponse(BaseModel):
    """
    Resposta após abrir a carta e resgatar
    o cupom (US-21).
    """

    carta_id: str

    semanas_sequencia: int = Field(
        ...,
        ge=0,
    )

    meta_sequencia: int = Field(
        default=META_SEQUENCIA,
        ge=1,
    )

    cupom: Cupom
    proxima_carta_em: str
