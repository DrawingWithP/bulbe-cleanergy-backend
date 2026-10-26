"""
Camada de Apresentação, CartaController (APIRouter).
Endpoints do Clube Bulbe: Cartas e situação de ofensiva (US-18, US-19, US-20 e US-21).
"""
from fastapi import APIRouter, Query, status

from app.domain.carta import (
    AberturaCartaResponse,
    Carta,
    CartaListaPaginada,
    ClubeSituacaoResponse,
    SituacaoCarta,
)
from app.services.carta_service import carta_service

router = APIRouter(tags=["Clube Bulbe e Cartas"])


@router.get(
    "/v1/clientes/{cliente_id}/clube",
    response_model=ClubeSituacaoResponse,
    summary="Consultar situação do cliente no Clube Bulbe (US-18)",
)
def obter_situacao_clube(cliente_id: str) -> ClubeSituacaoResponse:
    """Retorna a ofensiva de semanas do cliente e disponibilidade da próxima carta."""
    return carta_service.obter_situacao_clube(cliente_id)


@router.get(
    "/v1/clientes/{cliente_id}/cartas",
    response_model=CartaListaPaginada,
    summary="Listar histórico de cartas do cliente (US-19)",
)
def listar_cartas_cliente(
    cliente_id: str,
    page: int = Query(1, ge=1, description="Número da página"),
    limit: int = Query(20, ge=1, le=100, description="Itens por página"),
    situacao: SituacaoCarta | None = Query(None, description="Filtro por situação da carta"),
) -> CartaListaPaginada:
    """Lista o histórico de cartas semanais do cliente no Clube Bulbe."""
    return carta_service.listar_cartas_cliente(
        cliente_id=cliente_id,
        page=page,
        limit=limit,
        situacao=situacao,
    )


@router.get(
    "/v1/cartas/{carta_id}",
    response_model=Carta,
    summary="Consultar dados de uma carta específica (US-20)",
)
def buscar_carta(carta_id: str) -> Carta:
    """Retorna os dados de uma carta semanal do Clube Bulbe."""
    return carta_service.buscar_por_id(carta_id)


@router.post(
    "/v1/cartas/{carta_id}/abertura",
    response_model=AberturaCartaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Abrir carta semanal e resgatar cupom (US-21)",
)
def abrir_carta(carta_id: str) -> AberturaCartaResponse:
    """
    Abre a carta da semana, sorteia a recompensa e gera o cupom com validade de 14 dias.
    Ao completar 5 semanas consecutivas, libera o bônus especial.
    Operação idempotente: abrir uma carta já aberta retorna o mesmo cupom.
    """
    return carta_service.abrir_carta(carta_id)
