"""
Camada de Apresentacao, DicaController (APIRouter).
"""

from fastapi import (
    APIRouter,
    Depends,
    Query,
    status,
)

from app.core.dependencies import obter_usuario_atual
from app.domain.dica import (
    Dica,
    DicaCreate,
    DicaUpdate,
    VitrineDicas,
)
from app.domain.usuario import Usuario
from app.services.dica_service import dica_service


router = APIRouter(
    prefix="/v1/dicas",
    tags=["Dicas"],
)


@router.get(
    "",
    response_model=list[Dica],
)
def listar_dicas(
    todas: bool = Query(
        default=False,
        description="true: o acervo inteiro; padrao: so as 5 dicas da vitrine do app",
    ),
) -> list[Dica]:
    """
    Dicas exibidas no app (vitrine, na ordem do carrossel) ou o acervo inteiro.
    """

    return dica_service.listar(todas=todas)


@router.put(
    "/vitrine",
    response_model=list[Dica],
    summary="Definir as 5 dicas exibidas no app",
)
def definir_vitrine(
    dados: VitrineDicas,
    _usuario: Usuario = Depends(
        obter_usuario_atual
    ),
) -> list[Dica]:
    """
    Troca as 5 dicas do carrossel do app de uma vez, na ordem informada.

    Requer autenticacao.
    """

    return dica_service.definir_vitrine(dados.dicas)


@router.get(
    "/{dica_id}",
    response_model=Dica,
)
def buscar_dica(
    dica_id: int,
) -> Dica:
    """
    Retorna os dados de uma dica especifica.
    """

    return dica_service.buscar_por_id(
        dica_id
    )


@router.post(
    "",
    response_model=Dica,
    status_code=status.HTTP_201_CREATED,
)
def criar_dica(
    dados: DicaCreate,
    _usuario: Usuario = Depends(
        obter_usuario_atual
    ),
) -> Dica:
    """
    Cria uma nova dica.

    Requer autenticacao.
    """

    return dica_service.criar(
        dados
    )


@router.put(
    "/{dica_id}",
    response_model=Dica,
)
def atualizar_dica(
    dica_id: int,
    dados: DicaUpdate,
    _usuario: Usuario = Depends(
        obter_usuario_atual
    ),
) -> Dica:
    """
    Atualiza os dados de uma dica existente.

    Requer autenticacao.
    """

    return dica_service.atualizar(
        dica_id,
        dados,
    )


@router.delete(
    "/{dica_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remover_dica(
    dica_id: int,
    _usuario: Usuario = Depends(
        obter_usuario_atual
    ),
) -> None:
    """
    Remove uma dica especifica (US-30).

    Requer autenticacao.
    """

    dica_service.remover(
        dica_id
    )
