"""
Camada de Domínio, entidade Usina.
"""

from datetime import date
from enum import Enum

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class StatusUsina(str, Enum):
    ativa = "ativa"
    em_manutencao = "em_manutencao"
    inativa = "inativa"


class UsinaBase(BaseModel):
    nome: str = Field(
        ...,
        min_length=3,
        max_length=100,
        description="Nome da usina solar",
    )

    localizacao: str = Field(
        ...,
        min_length=3,
        max_length=100,
        description="Cidade e estado, ex: Uberlandia, MG",
    )

    capacidade_geracao_kwh: float = Field(
        ...,
        gt=0,
        description="Capacidade de geracao em kWh",
    )

    status: StatusUsina = StatusUsina.ativa


class UsinaCreate(UsinaBase):
    """
    Campos exigidos para criar uma usina (POST).
    """

    pass


class UsinaUpdate(BaseModel):
    """
    Campos que podem ser atualizados.
    Todos sao opcionais.
    """

    nome: str | None = Field(
        default=None,
        min_length=3,
        max_length=100,
    )

    localizacao: str | None = Field(
        default=None,
        min_length=3,
        max_length=100,
    )

    capacidade_geracao_kwh: float | None = Field(
        default=None,
        gt=0,
    )

    status: StatusUsina | None = None


class Usina(UsinaBase):
    """
    Representacao completa de uma usina,
    como a API devolve.
    """

    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    data_ativacao: date
