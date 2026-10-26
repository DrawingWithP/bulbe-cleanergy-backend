"""
Camada de Apresentação, CupomController (APIRouter).
Endpoints de Cupons de Desconto do Clube Bulbe (US-03, US-22 e US-23).
"""
from fastapi import APIRouter, Query, status

from app.domain.cupom import Cupom, CupomListaPaginada, CupomUpdate, SituacaoCupom
from app.services.cupom_service import cupom_service

router = APIRouter(tags=["Cupons"])


@router.get(
    "/v1/clientes/{cliente_id}/cupons",
    response_model=CupomListaPaginada,
    summary="Listar cupons do cliente (US-03)",
)
def listar_cupons_cliente(
    cliente_id: str,
    page: int = Query(1, ge=1, description="Número da página"),
    limit: int = Query(20, ge=1, le=100, description="Itens por página"),
    situacao: SituacaoCupom | None = Query(None, description="Filtro opcional por situação"),
) -> CupomListaPaginada:
    """Lista os cupons disponíveis ou salvos na carteira do cliente."""
    return cupom_service.listar_por_cliente(
        cliente_id=cliente_id,
        page=page,
        limit=limit,
        situacao=situacao,
    )


@router.get(
    "/v1/cupons/{cupom_id}",
    response_model=Cupom,
    summary="Consultar cupom por ID (US-22)",
)
def buscar_cupom(cupom_id: str) -> Cupom:
    """Retorna os dados detalhados de um cupom com código promocional."""
    return cupom_service.buscar_por_id(cupom_id)


@router.patch(
    "/v1/cupons/{cupom_id}",
    response_model=Cupom,
    summary="Atualizar situação do cupom (US-23)",
)
def atualizar_situacao_cupom(cupom_id: str, dados: CupomUpdate) -> Cupom:
    """Atualiza o status do cupom para 'salvo' ou 'usado'."""
    return cupom_service.atualizar_situacao(cupom_id, dados)


@router.delete(
    "/v1/cupons/{cupom_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Descartar cupom",
)
def descartar_cupom(cupom_id: str) -> None:
    """Descarta logicamente o cupom da lista do cliente."""
    cupom_service.descartar(cupom_id)
