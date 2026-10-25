"""
Camada de Domínio, entidades e esquemas da Jornada de Ativação CEMIG (US-11 e US-12).
"""
from enum import Enum
from pydantic import BaseModel, Field


class SituacaoEtapa(str, Enum):
    concluida = "concluida"
    atual = "atual"
    pendente = "pendente"


class EtapaDetalhe(BaseModel):
    numero: int
    nome: str
    titulo: str
    descricao: str
    situacao: SituacaoEtapa
    concluida_em: str | None = None


class EtapasListaResponse(BaseModel):
    data: list[EtapaDetalhe]
    total: int = 5


class AtivacaoResumoResponse(BaseModel):
    """Resumo da ativação para a tela de Conexão/Status (US-11)."""
    cliente_id: str
    etapa_atual: int
    total_etapas: int = 5
    percentual_concluido: int
    titulo: str
    descricao: str
    distribuidora: str
    prazo_ativacao_dias: int
    previsao_conclusao: str
    atualizado_em: str


class AtivacaoUpdateRequest(BaseModel):
    """Corpo para avançar ou corrigir etapa de ativação (PATCH /v1/clientes/{id}/ativacao - US-12)."""
    etapa_atual: int = Field(..., ge=1, le=5, description="Número da nova etapa (1 a 5)")
    observacao: str | None = Field(None, max_length=255, description="Observação opcional da mudança")


class AtivacaoAtualizadaResponse(BaseModel):
    cliente_id: str
    etapa_atual: int
    percentual_concluido: int
    titulo: str
    atualizado_em: str


class AtivacaoCliente(BaseModel):
    """Registro interno da ativação do cliente."""
    cliente_id: str
    etapa_atual: int = 1
    distribuidora: str = "CEMIG"
    prazo_ativacao_dias: int = 90
    previsao_conclusao: str = "2026-07-31"
    atualizado_em: str
    observacoes: list[str] = []

    class Config:
        from_attributes = True
