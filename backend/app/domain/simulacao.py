"""
Camada de Domínio, entidade Simulacao.
"""
from datetime import date
from enum import Enum
from pydantic import BaseModel, Field
class StatusSimulacao(str, Enum):
    ativa = "ativa"
    em_manutencao = "em_manutencao"
    inativa = "inativa"
class SimulacaoBase(BaseModel):
    valor_atual: float = Field(gt = 0)
    valor_proposto: float = Field(ge=0)
    periodo_meses: int = Field(gt=0)
    indicacoes: int = Field(gt=0)
class SimulacaoCreate(SimulacaoBase):
    """Campos exigidos para criar uma simulacao (POST)."""
    pass
class UsinaUpdate(BaseModel):
    """Campos que podem ser atualizados (PUT). Todos opcionais."""
    valor_atual: float | None = Field(gt=0)
    valor_proposto: float | None = Field(ge=0)
    periodo_meses: int | None = Field(gt=0)
    indicacoes: int | None = Field(gt=0)
class Simulacao(SimulacaoBase):
    """Representacao completa de uma simulacao, como a API devolve."""
    id: int
    data_ativacao: date
    class Config:
        from_attributes = True        