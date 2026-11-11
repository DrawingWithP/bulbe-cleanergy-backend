"""
Camada de Domínio, entidade Dica.
"""

from datetime import date
from enum import Enum

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class StatusDica(str, Enum):
    ativa = "ativa"
    em_manutencao = "em_manutencao"
    inativa = "inativa"


class DicaBase(BaseModel):
    titulo: str = Field(
        ...,
        min_length=3,
        max_length=100,
        description="Titulo da dica",
    )

    descricao: str = Field(
        ...,
        min_length=3,
        max_length=250,
        description="Resumo do que fazer para a dica",
    )

    economia: float = Field(
        ...,
        gt=0,
        description="Economia mensal da dica",
    )

    imagem_svg: str = Field(
        ...,
        min_length=1,
        description="Código XML/Texto puro do arquivo SVG",
    )


class DicaCreate(DicaBase):
    """
    Campos exigidos para criar uma dica (POST).
    """

    pass


class DicaUpdate(BaseModel):
    """
    Campos que podem ser atualizados.
    Todos são opcionais.
    """

    titulo: str | None = Field(
        default=None,
        min_length=3,
        max_length=100,
    )

    descricao: str | None = Field(
        default=None,
        min_length=3,
        max_length=250,
    )

    economia: float | None = Field(
        default=None,
        gt=0,
    )

    imagem_svg: str | None = Field(
        default=None,
        min_length=1,
    )


class Dica(DicaBase):
    """
    Representacao completa de uma dica,
    como a API devolve.
    """

    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    data_ativacao: date
