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


class IconeDica(str, Enum):
    """
    Icones prontos das dicas (o app mostra o desenho correspondente).
    Os 5 primeiros sao os icones originais do protótipo.
    """

    lampada_led = "lampada_led"
    lampada_apagada = "lampada_apagada"
    chuveiro = "chuveiro"
    maquina_lavar = "maquina_lavar"
    cofrinho = "cofrinho"
    geladeira = "geladeira"
    ar_condicionado = "ar_condicionado"
    tomada = "tomada"
    televisao = "televisao"
    ferro_passar = "ferro_passar"
    sol = "sol"
    ventilador = "ventilador"


TAMANHO_VITRINE = 5


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

    icone: IconeDica = Field(
        default=IconeDica.lampada_led,
        description="Icone pronto exibido no app",
    )

    imagem_svg: str | None = Field(
        default=None,
        min_length=1,
        description=(
            "Obsoleto: o app usa o campo icone. Mantido so por "
            "compatibilidade com clientes antigos da API."
        ),
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

    icone: IconeDica | None = None


class VitrineDicas(BaseModel):
    """
    Corpo do PUT /v1/dicas/vitrine: as 5 dicas exibidas no app, na ordem.
    """

    dicas: list[int] = Field(
        ...,
        min_length=TAMANHO_VITRINE,
        max_length=TAMANHO_VITRINE,
        description="Ids das 5 dicas, na ordem do carrossel",
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
    em_exibicao: bool = False
    ordem: int | None = None
