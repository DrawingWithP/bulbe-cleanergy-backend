"""
Camada de Apresentacao, atendimento pelo app (Fale conosco).

Cliente (mesmo modelo das demais rotas do cliente, sem token de cliente):
abrir conversa, listar, ler mensagens (com `depois_de` para o polling),
enviar mensagem e encerrar.
Operador (token): fila de atendimentos e resposta do atendente.
"""

from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import obter_usuario_atual
from app.domain.atendimento import (
    AbrirAtendimento,
    AtendimentoDetalhe,
    AtendimentoResumo,
    Encerramento,
    Mensagem,
    NovaMensagem,
    RespostaAtendente,
    StatusAtendimento,
)
from app.domain.usuario import Usuario
from app.services.atendimento_service import atendimento_service


router = APIRouter(tags=["Atendimento"])


@router.post(
    "/v1/atendimentos",
    response_model=AtendimentoDetalhe,
    status_code=status.HTTP_201_CREATED,
    summary="Abrir conversa (o robo responde na hora)",
)
def abrir_atendimento(dados: AbrirAtendimento) -> AtendimentoDetalhe:
    return atendimento_service.abrir(dados)


@router.get(
    "/v1/atendimentos",
    response_model=list[AtendimentoResumo],
    summary="Fila de atendimentos (operador)",
)
def fila_de_atendimentos(
    status_filtro: list[StatusAtendimento] | None = Query(default=None, alias="status"),
    _usuario: Usuario = Depends(obter_usuario_atual),
) -> list[AtendimentoResumo]:
    return atendimento_service.fila(status_filtro)


@router.get(
    "/v1/clientes/{cliente_id}/atendimentos",
    response_model=list[AtendimentoResumo],
    summary="Conversas do cliente",
)
def atendimentos_do_cliente(cliente_id: str) -> list[AtendimentoResumo]:
    return atendimento_service.listar_do_cliente(cliente_id)


@router.get(
    "/v1/atendimentos/{atendimento_id}",
    response_model=AtendimentoDetalhe,
    summary="Conversa com as mensagens",
)
def detalhar_atendimento(
    atendimento_id: str,
    depois_de: int = Query(default=0, ge=0, description="So mensagens com id maior (polling)"),
) -> AtendimentoDetalhe:
    return atendimento_service.detalhar(atendimento_id, depois_de)


@router.post(
    "/v1/atendimentos/{atendimento_id}/mensagens",
    response_model=list[Mensagem],
    status_code=status.HTTP_201_CREATED,
    summary="Mensagem do cliente",
)
def enviar_mensagem(atendimento_id: str, dados: NovaMensagem) -> list[Mensagem]:
    return atendimento_service.enviar_do_cliente(atendimento_id, dados.texto)


@router.post(
    "/v1/atendimentos/{atendimento_id}/respostas",
    response_model=Mensagem,
    status_code=status.HTTP_201_CREATED,
    summary="Resposta do atendente (operador)",
)
def responder_atendimento(
    atendimento_id: str,
    dados: RespostaAtendente,
    _usuario: Usuario = Depends(obter_usuario_atual),
) -> Mensagem:
    return atendimento_service.responder_como_atendente(atendimento_id, dados.texto, dados.atendente)


@router.post(
    "/v1/atendimentos/{atendimento_id}/encerramento",
    response_model=AtendimentoDetalhe,
    summary="Encerrar conversa (com nota opcional)",
)
def encerrar_atendimento(atendimento_id: str, dados: Encerramento) -> AtendimentoDetalhe:
    return atendimento_service.encerrar(atendimento_id, dados.avaliacao)
