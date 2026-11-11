"""
Camada de Apresentação, AtivacaoController (APIRouter).

Endpoints da Jornada de Ativação CEMIG do Cliente
(US-11 e US-12).
"""

from fastapi import (
    APIRouter,
    Depends,
)

from app.core.dependencies import obter_usuario_atual
from app.domain.ativacao import (
    AtivacaoAtualizadaResponse,
    AtivacaoResumoResponse,
    AtivacaoUpdateRequest,
    EtapasListaResponse,
)
from app.domain.usuario import Usuario
from app.services.ativacao_service import ativacao_service


router = APIRouter(
    prefix="/v1/clientes/{cliente_id}/ativacao",
    tags=["Ativacao"],
)


@router.get(
    "",
    response_model=AtivacaoResumoResponse,
    summary="Consultar status de ativação do cliente (US-11)",
)
def obter_resumo_ativacao(
    cliente_id: str,
) -> AtivacaoResumoResponse:
    """
    Retorna o resumo da jornada de ativação
    do cliente, incluindo percentual, etapa e prazos.
    """

    return ativacao_service.obter_resumo(
        cliente_id
    )


@router.get(
    "/etapas",
    response_model=EtapasListaResponse,
    summary="Listar as 5 etapas da jornada de ativação",
)
def listar_etapas_ativacao(
    cliente_id: str,
) -> EtapasListaResponse:
    """
    Lista as etapas da jornada de ativação
    e a situação individual de cada uma.
    """

    return ativacao_service.listar_etapas(
        cliente_id
    )


@router.patch(
    "",
    response_model=AtivacaoAtualizadaResponse,
    summary="Atualizar etapa de ativação do cliente (US-12)",
)
def atualizar_etapa_ativacao(
    cliente_id: str,
    dados: AtivacaoUpdateRequest,
    _usuario: Usuario = Depends(
        obter_usuario_atual
    ),
) -> AtivacaoAtualizadaResponse:
    """
    Avança ou ajusta a etapa atual da jornada
    de ativação junto à concessionária.

    Requer autenticação.
    """

    return ativacao_service.atualizar_etapa(
        cliente_id,
        dados,
    )
