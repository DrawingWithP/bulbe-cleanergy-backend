from typing import List

from fastapi import APIRouter, HTTPException, Response, Depends, status
from app.core.dependencies import obter_usuario_atual
from app.domain.usuario import Usuario

from app.domain.indicacao import Indicacao, IndicacaoCreate
from app.services.indicacao_service import (
    IndicacaoDuplicadaError,
    IndicacaoNaoEncontradaError,
    IndicacaoNaoPodeSerExcluidaError,
    indicacao_service,
)


router = APIRouter(tags=["Indicacoes"])


@router.post(
    "/v1/indicacoes",
    response_model=Indicacao,
    status_code=status.HTTP_201_CREATED,
)
def criar_indicacao(dados: IndicacaoCreate):
    try:
        return indicacao_service.criar(dados)

    except IndicacaoDuplicadaError as erro:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(erro),
        )


@router.get(
    "/v1/indicacoes/{indicacao_id}",
    response_model=Indicacao,
)
def consultar_indicacao(indicacao_id: int):
    try:
        return indicacao_service.buscar_por_id(indicacao_id)

    except IndicacaoNaoEncontradaError as erro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(erro),
        )


@router.get(
    "/v1/clientes/{cliente_id}/indicacoes",
    response_model=List[Indicacao],
)
def consultar_indicacoes_cliente(cliente_id: int):
    return indicacao_service.listar_por_cliente(cliente_id)


@router.delete(
    "/v1/indicacoes/{indicacao_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def excluir_indicacao(indicacao_id: int, usuario: Usuario = Depends(obter_usuario_atual)):
    try:
        indicacao_service.excluir(indicacao_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    except IndicacaoNaoEncontradaError as erro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(erro),
        )

    except IndicacaoNaoPodeSerExcluidaError as erro:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(erro),
        ) 