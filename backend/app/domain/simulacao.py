"""
Camada de Domínio, entidade Simulacao.
"""

from datetime import date

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class SimulacaoBase(BaseModel):
    valor_atual: float = Field(
        ...,
        gt=0,
        description="Valor atual da conta de energia",
    )

    valor_proposto: float = Field(
        ...,
        ge=0,
        description="Valor proposto após a simulação",
    )

    periodo_meses: int = Field(
        ...,
        gt=0,
        description="Período da simulação em meses",
    )

    indicacoes: int = Field(
        ...,
        ge=0,
        description="Quantidade de indicações consideradas",
    )


class SimulacaoCreate(SimulacaoBase):
    """
    Campos exigidos para criar uma simulacao (POST).
    """

    pass


class Simulacao(BaseModel):
    """
    Representacao completa de uma simulacao,
    como a API devolve.
    """

    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    valor_atual: float
    valor_proposto: float
    periodo_meses: int
    indicacoes: int
    data_ativacao: date
