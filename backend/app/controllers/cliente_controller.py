"""
Camada de Apresentação, ClienteController (APIRouter).
Endpoints de gerenciamento e perfil de Clientes (US-05, US-31 e US-34).
"""
from fastapi import APIRouter, Query, Depends, status
from app.core.dependencies import obter_usuario_atual
from app.domain.usuario import Usuario

from app.domain.cliente import (
    Cliente,
    ClienteCreate,
    ClienteCriadoResponse,
    ClienteListaPaginada,
    ClienteUpdate,
    StatusCliente,
)
from app.services.cliente_service import cliente_service

router = APIRouter(prefix="/v1/clientes", tags=["Clientes"])


@router.get(
    "",
    response_model=ClienteListaPaginada,
    summary="Listar clientes com paginação (Uso administrativo)",
)
def listar_clientes(
    page: int = Query(1, ge=1, description="Número da página"),
    limit: int = Query(20, ge=1, le=100, description="Itens por página"),
    status: StatusCliente | None = Query(None, description="Filtro opcional por status"),
) -> ClienteListaPaginada:
    """Retorna listagem paginada de clientes da Bulbe."""
    return cliente_service.listar(page=page, limit=limit, status_filtro=status)


@router.post(
    "",
    response_model=ClienteCriadoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar novo cliente (US-31)",
)
def criar_cliente(dados: ClienteCreate) -> ClienteCriadoResponse:
    """Cria um novo cliente no sistema após a aprovação da adesão."""
    return cliente_service.criar(dados)


@router.get(
    "/{cliente_id}",
    response_model=Cliente,
    summary="Buscar dados de um cliente específico (US-05)",
)
def buscar_cliente(cliente_id: str) -> Cliente:
    """Retorna os dados cadastrais completos de um cliente."""
    return cliente_service.buscar_por_id(cliente_id)


@router.put(
    "/{cliente_id}",
    response_model=Cliente,
    summary="Atualizar dados cadastrais do cliente (US-34)",
)
def atualizar_cliente(cliente_id: str, dados: ClienteUpdate, usuario: Usuario = Depends(obter_usuario_atual)) -> Cliente:
    """Atualiza informações de perfil ou endereço do cliente."""
    return cliente_service.atualizar(cliente_id, dados)


@router.delete(
    "/{cliente_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remover cliente",
)
def remover_cliente(cliente_id: str,  usuario: Usuario = Depends(obter_usuario_atual)) -> None:
    """Remove um cliente do sistema."""
    cliente_service.remover(cliente_id)
