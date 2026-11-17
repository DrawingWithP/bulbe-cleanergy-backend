"""
Camada de Dominio, bandeiras tarifarias (RF-03).

A bandeira tarifaria e definida pela ANEEL todo mes e acrescenta um valor
por kWh consumido na conta de luz. O simulador usa a bandeira vigente para
projetar a conta e a economia com a Bulbe.

Os valores abaixo sao de referencia (R$ por kWh, ANEEL 2025: amarela
R$ 1,885, vermelha patamar 1 R$ 4,463 e vermelha patamar 2 R$ 7,877 a cada
100 kWh). Quando a ANEEL reajustar, basta atualizar ADICIONAL_POR_KWH.
"""

import re
from datetime import datetime
from enum import Enum

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class BandeiraTarifaria(str, Enum):
    verde = "verde"
    amarela = "amarela"
    vermelha_1 = "vermelha_1"
    vermelha_2 = "vermelha_2"


ADICIONAL_POR_KWH: dict[BandeiraTarifaria, float] = {
    BandeiraTarifaria.verde: 0.0,
    BandeiraTarifaria.amarela: 0.01885,
    BandeiraTarifaria.vermelha_1: 0.04463,
    BandeiraTarifaria.vermelha_2: 0.07877,
}

# Tarifa media residencial (R$/kWh, com impostos) usada para estimar o
# consumo a partir do valor da conta informado no simulador.
TARIFA_MEDIA_KWH = 0.95

BANDEIRA_PADRAO = BandeiraTarifaria.verde

PADRAO_MES_REFERENCIA = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def mes_referencia_valido(mes_referencia: str) -> bool:
    """Confere o formato AAAA-MM (mes de 01 a 12)."""

    return bool(PADRAO_MES_REFERENCIA.match(mes_referencia))


def mes_referencia_atual(agora: datetime | None = None) -> str:
    """Mes corrente no formato AAAA-MM (segue o relogio da demonstracao)."""

    from app.core import relogio

    return (agora or relogio.agora()).strftime("%Y-%m")


class BandeiraUpdate(BaseModel):
    """
    Corpo do PUT /v1/bandeiras/{mes_referencia}.
    """

    bandeira: BandeiraTarifaria


class BandeiraMes(BaseModel):
    """
    Bandeira vigente em um mes, como a API devolve.
    """

    model_config = ConfigDict(
        from_attributes=True
    )

    mes_referencia: str = Field(
        ...,
        description="Mes de referencia no formato AAAA-MM",
    )

    bandeira: BandeiraTarifaria

    adicional_por_kwh: float = Field(
        default=0.0,
        description="Acrescimo da bandeira em R$ por kWh",
    )

    definida: bool = Field(
        default=True,
        description=(
            "False quando o mes ainda nao foi cadastrado "
            "e a API usa a bandeira padrao (verde)"
        ),
    )

    atualizado_em: datetime | None = None
