"""
Camada de Apresentacao, IndicacaoController (APIRouter).
"""

from fastapi import (
    APIRouter,
    Depends,
    status,
)

from app.core.dependencies import obter_usuario_atual
from app.domain.indicacao import (
    Indicacao,
    IndicacaoCreate,
)
from app.domain.usuario import Usuario
from app.services.indicacao_service import indicacao_service


router = APIRouter(
    tags=["Indicacoes"],
)


@router.post(
    "/v1/indicacoes",
    response_model=Indicacao,
    status_code=status.HTTP_201_CREATED,
)
def criar_indicacao(
    dados: IndicacaoCreate,
) -> Indicacao:
    """
    Cria uma nova indicacao.
    """

    return indicacao_service.criar(dados)


@router.get(
    "/v1/indicacoes/{indicacao_id}",
    response_model=Indicacao,
)
def consultar_indicacao(
    indicacao_id: int,
) -> Indicacao:
    """
    Retorna uma indicacao especifica.
    """

    return indicacao_service.buscar_por_id(
        indicacao_id
    )


@router.get(
    "/v1/clientes/{cliente_id}/indicacoes",
    response_model=list[Indicacao],
)
def consultar_indicacoes_cliente(
    cliente_id: int,
) -> list[Indicacao]:
    """
    Lista todas as indicacoes realizadas
    por um cliente.
    """

    return indicacao_service.listar_por_cliente(
        cliente_id
    )


@router.delete(
    "/v1/indicacoes/{indicacao_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def excluir_indicacao(
    indicacao_id: int,
    _usuario: Usuario = Depends(
        obter_usuario_atual
    ),
) -> None:
    """
    Exclui uma indicacao que ente.

    Requer autenticacao.
    """

    indicacao_service.excluir(
        indicacao_id
    )
