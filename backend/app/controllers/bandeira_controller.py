"""
Camada de Apresentacao, BandeiraController (APIRouter).

Bandeira tarifaria vigente por mes, usada pelo simulador (RF-03).
"""

from fastapi import (
    APIRouter,
    Depends,
)

from app.core.dependencies import obter_usuario_atual
from app.domain.bandeira import (
    BandeiraMes,
    BandeiraUpdate,
)
from app.domain.usuario import Usuario
from app.services.bandeira_service import bandeira_service


router = APIRouter(
    prefix="/v1/bandeiras",
    tags=["Bandeiras tarifarias"],
)


@router.get(
    "",
    response_model=list[BandeiraMes],
    summary="Listar bandeiras cadastradas",
)
def listar_bandeiras() -> list[BandeiraMes]:
    """
    Lista as bandeiras cadastradas, do mes mais recente ao mais antigo.
    """

    return bandeira_service.listar()


@router.get(
    "/atual",
    response_model=BandeiraMes,
    summary="Bandeira do mes atual",
)
def consultar_bandeira_atual() -> BandeiraMes:
    """
    Bandeira vigente no mes atual. Sem cadastro, devolve verde
    com definida=false.
    """

    return bandeira_service.obter()


@router.get(
    "/{mes_referencia}",
    response_model=BandeiraMes,
    summary="Bandeira de um mes",
)
def consultar_bandeira(
    mes_referencia: str,
) -> BandeiraMes:
    """
    Bandeira de um mes no formato AAAA-MM.
    """

    return bandeira_service.obter(mes_referencia)


@router.put(
    "/{mes_referencia}",
    response_model=BandeiraMes,
    summary="Definir a bandeira de um mes",
)
def definir_bandeira(
    mes_referencia: str,
    dados: BandeiraUpdate,
    _usuario: Usuario = Depends(
        obter_usuario_atual
    ),
) -> BandeiraMes:
    """
    Cadastra ou altera a bandeira de um mes.

    Requer autenticacao.
    """

    return bandeira_service.definir(
        mes_referencia,
        dados.bandeira,
    )
