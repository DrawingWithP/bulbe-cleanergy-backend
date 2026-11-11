"""
Camada de Domínio, entidades e esquemas da Jornada de Ativação CEMIG
(US-11 e US-12).
"""

from enum import Enum

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


TOTAL_ETAPAS = 5
PRAZO_ATIVACAO_DIAS = 90


class SituacaoEtapa(str, Enum):
    concluida = "concluida"
    atual = "atual"
    pendente = "pendente"


class EtapaDetalhe(BaseModel):
    numero: int = Field(
        ...,
        ge=1,
        le=TOTAL_ETAPAS,
    )
    nome: str
    titulo: str
    descricao: str
    situacao: SituacaoEtapa
    concluida_em: str | None = None


class EtapasListaResponse(BaseModel):
    data: list[EtapaDetalhe]
    total: int = TOTAL_ETAPAS


class AtivacaoResumoResponse(BaseModel):
    """
    Resumo da ativação para a tela
    de Conexão/Status (US-11).
    """

    cliente_id: str
    etapa_atual: int = Field(
        ...,
        ge=1,
        le=TOTAL_ETAPAS,
    )
    total_etapas: int = TOTAL_ETAPAS
    percentual_concluido: int = Field(
        ...,
        ge=0,
        le=100,
    )
    titulo: str
    descricao: str
    distribuidora: str
    prazo_ativacao_dias: int = Field(
        ...,
        gt=0,
    )
    previsao_conclusao: str
    atualizado_em: str


class AtivacaoUpdateRequest(BaseModel):
    """
    Corpo para avançar ou corrigir a etapa de ativação.

    PATCH /v1/clientes/{id}/ativacao
    US-12.
    """

    etapa_atual: int = Field(
        ...,
        ge=1,
        le=TOTAL_ETAPAS,
        description="Número da nova etapa (1 a 5)",
    )

    observacao: str | None = Field(
        default=None,
        max_length=255,
        description="Observação opcional da mudança",
    )


class AtivacaoAtualizadaResponse(BaseModel):
    cliente_id: str
    etapa_atual: int = Field(
        ...,
        ge=1,
        le=TOTAL_ETAPAS,
    )
    percentual_concluido: int = Field(
        ...,
        ge=0,
        le=100,
    )
    titulo: str
    atualizado_em: str


class AtivacaoCliente(BaseModel):
    """
    Registro interno da ativação do cliente.
    """

    model_config = ConfigDict(
        from_attributes=True
    )

    cliente_id: str

    etapa_atual: int = Field(
        default=1,
        ge=1,
        le=TOTAL_ETAPAS,
    )

    distribuidora: str = "CEMIG"

    prazo_ativacao_dias: int = Field(
        default=PRAZO_ATIVACAO_DIAS,
        gt=0,
    )

    previsao_conclusao: str

    atualizado_em: str

    observacoes: list[str] = Field(
        default_factory=list
    )
