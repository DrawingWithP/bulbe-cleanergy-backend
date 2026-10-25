"""
Camada de Apresentação, PrimeiroAcessoController (APIRouter).
Endpoints para o fluxo de 'É minha primeira vez no app' (US-09 e US-10).
"""
from fastapi import APIRouter, status

from app.domain.primeiro_acesso import (
    ConfirmacaoRequest,
    ConfirmacaoResponse,
    VerificacaoRequest,
    VerificacaoResponse,
)
from app.services.primeiro_acesso_service import primeiro_acesso_service

router = APIRouter(prefix="/v1/primeiro-acesso", tags=["Primeiro Acesso"])


@router.post(
    "/verificacoes",
    response_model=VerificacaoResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Verificar CPF e enviar código no primeiro acesso (US-09)",
)
def solicitar_verificacao(dados: VerificacaoRequest) -> VerificacaoResponse:
    """
    Atende ao acionamento do botão 'É minha primeira vez no app' no front-end.
    Verifica se o CPF informado pertence a um cliente pré-cadastrado na Bulbe
    e dispara o código de confirmação para o contato cadastrado.
    """
    return primeiro_acesso_service.solicitar_verificacao(dados)


@router.post(
    "/confirmacoes",
    response_model=ConfirmacaoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Confirmar código e habilitar acesso do cliente (US-10)",
)
def confirmar_codigo(dados: ConfirmacaoRequest) -> ConfirmacaoResponse:
    """
    Confirma o código recebido via WhatsApp/SMS pelo cliente e habilita o acesso
    do cliente à área autenticada do aplicativo Bulbe.
    """
    return primeiro_acesso_service.confirmar_codigo(dados)
