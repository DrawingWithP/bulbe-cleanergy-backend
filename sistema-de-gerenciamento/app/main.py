"""
Ponto de entrada do Sistema de Gerenciamento (painel interno + chatbot).
"""
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

from app.chatbot.controller import router as chatbot_router
from app.database.conexao import inicializar_banco
from app.erros import ErroDeNegocio
from app.painel.controller import router as painel_router

PASTA_ESTATICA_PAINEL = Path(__file__).parent / "painel" / "static"


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    """Cria as tabelas e popula o banco ficticio na primeira execucao."""
    inicializar_banco()
    yield


app = FastAPI(
    title="Bulbe Energia, Sistema de Gerenciamento",
    description="Painel de gestao interno com chatbot (Claude Haiku) sobre um banco de dados ficticio.",
    version="1.0.0",
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
