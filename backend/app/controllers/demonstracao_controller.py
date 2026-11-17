"""
Camada de Apresentacao, DemonstracaoController (APIRouter).

Relogio de demonstracao: permite "pular dias" na apresentacao para mostrar
o Clube Bulbe liberando cartas, cupons vencendo e prazos andando.
So funciona fora de producao; adiantar e resetar exigem token de operador.
"""

from fastapi import APIRouter, Depends

from app.core.dependencies import obter_usuario_atual
from app.domain.usuario import Usuario
from app.services.demonstracao_service import (
    AvancarRelogio,
    RelogioDemonstracao,
    demonstracao_service,
)


router = APIRouter(
    prefix="/v1/demonstracao/relogio",
    tags=["Demonstracao"],
)


@router.get(
    "",
    response_model=RelogioDemonstracao,
    summary="Data usada pela API (com os dias adiantados)",
)
def consultar_relogio() -> RelogioDemonstracao:
    """Data e hora que a API esta usando e quantos dias foram adiantados."""

    return demonstracao_service.estado()


@router.post(
    "/avancar",
    response_model=RelogioDemonstracao,
    summary="Adiantar o relogio (somente demonstracao)",
)
def avancar_relogio(
    dados: AvancarRelogio,
    _usuario: Usuario = Depends(obter_usuario_atual),
) -> RelogioDemonstracao:
    """
    Adianta o relogio da API em alguns dias. Requer autenticacao e
    responde 404 em producao.
    """

    return demonstracao_service.avancar(dados.dias)


@router.post(
    "/resetar",
    response_model=RelogioDemonstracao,
    summary="Voltar o relogio para a data real (somente demonstracao)",
)
def resetar_relogio(
    _usuario: Usuario = Depends(obter_usuario_atual),
) -> RelogioDemonstracao:
    """Volta o relogio para hoje. Requer autenticacao."""

    return demonstracao_service.resetar()
