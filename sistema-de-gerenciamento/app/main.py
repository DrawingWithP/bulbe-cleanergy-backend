"""
Ponto de entrada do Sistema de Gerenciamento (painel interno + chatbot).
"""
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

try:
    # Carrega o .env antes de importar os modulos que leem variaveis de ambiente.
    from dotenv import load_dotenv

    load_dotenv(override=False)
except ImportError:  # python-dotenv e opcional
    pass

from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

import asyncio

from app.chatbot.controller import router as chatbot_router
from app.database.conexao import inicializar_banco
from app.integracao import sincronizacao
from app.integracao.config import obter_config
from app.erros import ErroDeNegocio
from app.painel.controller import router as painel_router

PASTA_ESTATICA_PAINEL = Path(__file__).parent / "painel" / "static"

logger = logging.getLogger(__name__)


def _expurgar_dados_antigos() -> None:
    """Aplica a retencao de dados (LGPD) configurada no .env; uma falha aqui nao impede o servidor de subir."""
    try:
        from app.database.consultas import expurgar_dados_antigos

        removidos = expurgar_dados_antigos(
            dias_chat=int(os.getenv("CHAT_RETENCAO_DIAS", "180")),
            dias_auditoria=int(os.getenv("AUDITORIA_RETENCAO_DIAS", "730")),
        )
        if any(removidos.values()):
            logger.info("Expurgo de dados antigos: %s", removidos)
    except Exception:  # noqa: BLE001
        logger.exception("Nao foi possivel aplicar a retencao de dados ao subir o servidor.")


async def _sincronizar_periodicamente(intervalo: int) -> None:
    """Traz os dados do app para o painel a cada `intervalo` segundos (em uma thread, sem travar a API)."""
    while True:
        await asyncio.sleep(intervalo)
        await asyncio.to_thread(sincronizacao.sincronizar_sem_erro)


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    """
    Cria as tabelas, popula o banco ficticio na primeira execucao, aplica a retencao de dados
    e liga a integracao com o app (sincronizacao ao subir e a cada INTEGRACAO_INTERVALO_SEGUNDOS).
    """
    inicializar_banco()
    _expurgar_dados_antigos()

    tarefa = None
    config = obter_config()
    if config.ativa:
        await asyncio.to_thread(sincronizacao.sincronizar_sem_erro)
        if config.intervalo_segundos > 0:
            tarefa = asyncio.create_task(_sincronizar_periodicamente(config.intervalo_segundos))
    else:
        logger.info("Integracao com o app desligada: %s", config.motivo_desligada)
    try:
        yield
    finally:
        if tarefa is not None:
            tarefa.cancel()


app = FastAPI(
    title="Bulbe Energia, Sistema de Gerenciamento",
    description=(
        "Painel de gestao interno com chatbot (Claude Haiku). Os dados do app (pasta backend/) sao "
        "sincronizados com o banco do painel, que completa com dados ficticios de faturas e atendimentos."
    ),
    version="2.0.0",
    lifespan=ciclo_de_vida,
)


@app.exception_handler(ErroDeNegocio)
def tratar_erro_de_negocio(request: Request, exc: ErroDeNegocio) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "status": exc.status,
            }
        },
    )


@app.exception_handler(StarletteHTTPException)
async def tratar_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Devolve {"error": {...}} puro quando o detail ja vem no formato padrao (painel/chatbot)."""
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail, headers=exc.headers)
    return await http_exception_handler(request, exc)


app.include_router(painel_router)
app.include_router(chatbot_router)

app.mount("/painel", StaticFiles(directory=PASTA_ESTATICA_PAINEL, html=True), name="painel")


@app.get("/", include_in_schema=False)
def raiz() -> RedirectResponse:
    return RedirectResponse(url="/painel/")


@app.get("/painel", include_in_schema=False)
def redirecionar_painel() -> RedirectResponse:
    return RedirectResponse(url="/painel/")
