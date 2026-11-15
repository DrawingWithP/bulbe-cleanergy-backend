"""
Camada de Domínio, entidade Simulacao.
"""

from datetime import date

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

from app.domain.bandeira import BandeiraTarifaria


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

    cliente_id e bandeira sao opcionais: o simulador aberto nao tem
    cliente, e sem bandeira a API usa a bandeira vigente no mes (RF-03).
    """

    cliente_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=36,
        description="Cliente que simulou (simulador logado)",
    )

    bandeira: BandeiraTarifaria | None = Field(
        default=None,
        description=(
            "Bandeira tarifaria usada no calculo. "
            "Vazio = bandeira vigente no mes atual"
        ),
    )


class SimulacaoCalculada(SimulacaoBase):
    """
    Simulacao com a economia ja calculada pelo servico,
    pronta para ser gravada.
    """

    cliente_id: str | None = None
    bandeira: BandeiraTarifaria
    economia_mensal: float = Field(..., ge=0)
    economia_total: float = Field(..., ge=0)


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
    cliente_id: str | None = None
    bandeira: BandeiraTarifaria = BandeiraTarifaria.verde
    economia_mensal: float | None = None
    economia_total: float | None = None
