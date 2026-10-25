"""
Camada de Apresentacao, AdesaoController (APIRouter).
"""
from fastapi import APIRouter, status

from app.domain.adesao import Adesao, AdesaoCreate, AdesaoUpdate
from app.services.adesao_service import adesao_service

router = APIRouter(prefix="/v1/adesoes", tags=["Adesoes"])

@router.get("", response_model=list[Adesao])
def listar_adesoes() -> list[Adesao]:
    """Lista todas as adesões cadastradas."""
    return adesao_service.listar()

@router.get("/{adesao_id}", response_model=Adesao)
def buscar_adesoes(adesao_id: int) -> Adesao:
    """Retorna os dados de uma adesao especifica."""
    return adesao_service.buscar_por_id(adesao_id)

@router.post("", response_model=Adesao, status_code=status.HTTP_201_CREATED)
def criar_adesao(dados: AdesaoCreate) -> Adesao:
    """Cria uma nova adesao."""
    return adesao_service.criar(dados)

@router.put("/{adesao_id}", response_model=Adesao)
def atualizar_Adesao(adesao_id: int, dados: AdesaoUpdate) -> Adesao:
    """Atualiza os dados de uma adesao existente."""
    return adesao_service.atualizar(adesao_id, dados)

@router.delete("/{adesao_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover_adesao(adesao_id: int) -> None:
    """Remove uma adesao."""
    adesao_service.remover(adesao_id)