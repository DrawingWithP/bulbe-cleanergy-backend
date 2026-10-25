"""
Camada de Apresentação, ParceiroController (APIRouter).
Endpoints do catálogo de parceiros do Clube Bulbe (US-02, US-24, US-25, US-26 e US-33).
"""
from fastapi import APIRouter, Query, status

from app.domain.parceiro import (
    Parceiro,
    ParceiroCreate,
    ParceiroCriadoResponse,
    ParceiroListaPaginada,
    ParceiroUpdate,
)
from app.services.parceiro_service import parceiro_service

router = APIRouter(prefix="/v1/parceiros", tags=["Parceiros"])


@router.get(
    "",
    response_model=ParceiroListaPaginada,
    summary="Listar parceiros do Clube Bulbe (US-02 e US-33)",
)
def listar_parceiros(
    page: int = Query(1, ge=1, description="Número da página"),
    limit: int = Query(20, ge=1, le=100, description="Itens por página"),
    categoria: str | None = Query(None, description="Filtro opcional por categoria"),
    ativo: bool | None = Query(None, description="Filtro opcional por status ativo"),
) -> ParceiroListaPaginada:
    """Lista os parceiros comerciais credenciados no Clube Bulbe."""
    return parceiro_service.listar(page=page, limit=limit, categoria=categoria, ativo=ativo)


@router.post(
    "",
    response_model=ParceiroCriadoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar novo parceiro (US-24)",
)
def criar_parceiro(dados: ParceiroCreate) -> ParceiroCriadoResponse:
    """Cadastra uma nova empresa parceira no Clube Bulbe."""
    return parceiro_service.criar(dados)


@router.get(
    "/{parceiro_id}",
    response_model=Parceiro,
    summary="Consultar dados de um parceiro específico (US-25)",
)
def buscar_parceiro(parceiro_id: str) -> Parceiro:
    """Retorna os detalhes de um parceiro pelo seu identificador único."""
    return parceiro_service.buscar_por_id(parceiro_id)


@router.put(
    "/{parceiro_id}",
    response_model=Parceiro,
    summary="Atualizar dados de um parceiro",
)
def atualizar_parceiro(parceiro_id: str, dados: ParceiroUpdate) -> Parceiro:
    """Atualiza as informações cadastrais de um parceiro existente."""
    return parceiro_service.atualizar(parceiro_id, dados)


@router.delete(
    "/{parceiro_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remover parceiro do Clube Bulbe (US-26)",
)
def remover_parceiro(parceiro_id: str) -> None:
    """Remove um parceiro credenciado do Clube."""
    parceiro_service.remover(parceiro_id)
