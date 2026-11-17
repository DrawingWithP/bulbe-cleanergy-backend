"""
Camada de Apresentacao, catalogo de cupons do Clube Bulbe.

Uso administrativo (sistema de gerenciamento): todas as rotas exigem token
de operador. O app nao le o catalogo diretamente: ele recebe o cupom ja
sorteado ao abrir a carta da semana.
"""

from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import obter_usuario_atual
from app.domain.cupom_catalogo import (
    CupomCatalogo,
    CupomCatalogoCreate,
    CupomCatalogoUpdate,
)
from app.services.cupom_catalogo_service import cupom_catalogo_service


router = APIRouter(
    prefix="/v1/catalogo-cupons",
    tags=["Catalogo de cupons"],
    dependencies=[Depends(obter_usuario_atual)],
)


@router.get("", response_model=list[CupomCatalogo], summary="Listar o catalogo")
def listar_catalogo(
    parceiro_id: str | None = Query(default=None, max_length=36),
    apenas_ativos: bool = Query(default=False),
) -> list[CupomCatalogo]:
    return cupom_catalogo_service.listar(parceiro_id, apenas_ativos)


@router.post(
    "",
    response_model=CupomCatalogo,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar cupom no catalogo",
)
def criar_modelo(dados: CupomCatalogoCreate) -> CupomCatalogo:
    return cupom_catalogo_service.criar(dados)


@router.get("/{modelo_id}", response_model=CupomCatalogo, summary="Consultar cupom do catalogo")
def buscar_modelo(modelo_id: str) -> CupomCatalogo:
    return cupom_catalogo_service.buscar_por_id(modelo_id)


@router.patch("/{modelo_id}", response_model=CupomCatalogo, summary="Alterar cupom do catalogo")
def atualizar_modelo(modelo_id: str, dados: CupomCatalogoUpdate) -> CupomCatalogo:
    return cupom_catalogo_service.atualizar(modelo_id, dados)


@router.delete(
    "/{modelo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remover cupom do catalogo",
)
def remover_modelo(modelo_id: str) -> None:
    cupom_catalogo_service.remover(modelo_id)
