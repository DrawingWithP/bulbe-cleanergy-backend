"""
Camada de Apresentacao, rotas de operacao do painel sobre o app.

Tudo o que o funcionario altera no app passa por aqui e e enviado para a API
do app (app/integracao/api_app.py), que e a fonte da verdade. Depois de cada
alteracao o painel sincroniza na hora, para a tela ja mostrar o resultado.

Rotas (prefixo /v1/painel):
- relogio de demonstracao: GET /demonstracao/relogio, POST .../avancar e .../resetar (admin)
"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.integracao import api_app, sincronizacao
from app.painel.auth import exigir_admin, funcionario_logado

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/painel", tags=["Painel: operacoes no app"])


def erro_http(erro: api_app.ErroApiApp) -> HTTPException:
    """ErroApiApp -> HTTPException no formato {"error": {...}} do painel."""
    return HTTPException(
        status_code=erro.status,
        detail={"error": {"code": erro.code, "message": erro.message, "status": erro.status}},
    )


def no_app(funcao, *args, sincronizar: bool = True, **kwargs):
    """Executa a operacao na API do app e, se der certo, sincroniza o painel."""
    try:
        resultado = funcao(*args, **kwargs)
    except api_app.ErroApiApp as erro:
        raise erro_http(erro) from erro
    if sincronizar:
        sincronizacao.sincronizar_sem_erro()
    return resultado


# ---------------------------------------------------------------------------
# Relogio de demonstracao
# ---------------------------------------------------------------------------
class AvancarRelogio(BaseModel):
    dias: int = Field(..., ge=1, le=60)


@router.get("/demonstracao/relogio", dependencies=[Depends(funcionario_logado)])
def relogio() -> dict:
    """Data que a API do app esta usando (com os dias adiantados)."""
    return no_app(api_app.relogio, sincronizar=False)


@router.post("/demonstracao/relogio/avancar")
def avancar_relogio(dados: AvancarRelogio, admin: dict = Depends(exigir_admin)) -> dict:
    """Adianta o relogio do app (somente admin e somente fora de producao)."""
    logger.info("Relogio de demonstracao +%s dia(s) por funcionario %s", dados.dias, admin.get("id"))
    return no_app(api_app.avancar_relogio, dados.dias)


@router.post("/demonstracao/relogio/resetar")
def resetar_relogio(admin: dict = Depends(exigir_admin)) -> dict:
    """Volta o relogio do app para a data real (somente admin)."""
    return no_app(api_app.resetar_relogio)
