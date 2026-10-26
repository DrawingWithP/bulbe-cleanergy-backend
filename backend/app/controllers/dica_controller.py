"""
Camada de Apresentacao, DicaController (APIRouter).
"""
from fastapi import APIRouter, Depends, status
from app.core.dependencies import obter_usuario_atual
from app.domain.usuario import Usuario

from app.domain.dica import Dica, DicaCreate, DicaUpdate
from app.services.dica_service import dica_service

router = APIRouter(prefix="/v1/dicas", tags=["Dicas"])


@router.get("", response_model=list[Dica])
def listar_dicas() -> list[Dica]:
    """Lista todas as dicas cadastradas."""
    return dica_service.listar()


@router.get("/{dica_id}", response_model=Dica)
def buscar_dica(dica_id: int) -> Dica:
    """Retorna os dados de uma dica especifica."""
    return dica_service.buscar_por_id(dica_id)


@router.post("", response_model=Dica, status_code=status.HTTP_201_CREATED)
def criar_dica(dados: DicaCreate, usuario: Usuario = Depends(obter_usuario_atual)) -> Dica:
    """Cria uma nova dica."""
    return dica_service.criar(dados)


@router.put("/{dica_id}", response_model=Dica)
def atualizar_dica(dica_id: int, dados: DicaUpdate, usuario: Usuario = Depends(obter_usuario_atual)) -> Dica:
    """Atualiza os dados de uma dica existente."""
    return dica_service.atualizar(dica_id, dados)


@router.delete("/{dica_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover_dica(dica_id: int, usuario: Usuario = Depends(obter_usuario_atual)) -> None:
    """Remove uma dica especifica (US-30)."""
    dica_service.remover(dica_id)
