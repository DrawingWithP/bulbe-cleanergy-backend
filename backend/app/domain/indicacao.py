"""
Camada de Dominio, entidade Indicacao.
"""
from enum import Enum
from pydantic import BaseModel, Field


class StatusIndicacao(str, Enum):
    pendente = "pendente"
    aderiu = "aderiu"
    cancelada = "cancelada"


class IndicacaoBase(BaseModel):
    cliente_id: int = Field(..., gt=0, description="ID do cliente que realizou a indicacao")
    nome: str = Field(..., min_length=3, max_length=100, description="Nome da pessoa indicada")
    contato: str = Field(..., min_length=5, max_length=100, description="Email ou telefone da pessoa indicada")


class IndicacaoCreate(IndicacaoBase):
    """Campos exigidos para criar uma indicacao (POST)."""
    pass


class Indicacao(IndicacaoBase):
    """Representacao completa de uma indicacao."""
    id: int
    situacao: StatusIndicacao = StatusIndicacao.pendente
    bonus: float = 50.0

    class Config:
        from_attributes = True