"""
Ponto de entrada da aplicacao.
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
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.exception_handlers import http_exception_handler
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.controllers.usina_controller import router as usina_router
from app.controllers.dica_controller import router as dica_router
from app.painel.controller import router as painel_router
from app.chatbot.controller import router as chatbot_router
from app.database.conexao import inicializar_banco
from app.services.usina_service import ErroDeNegocio as ErroDeNegocioUsina
from app.services.dica_service import ErroDeNegocio as ErroDeNegocioDica

PASTA_ESTATICA_PAINEL = Path(__file__).parent / "painel" / "static"


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    """Cria as tabelas e popula o banco ficticio na primeira execucao."""
    inicializar_banco()
    yield


app = FastAPI(
    title="Bulbe Energia, API",
    description=(
        "Handson de CRUD em FastAPI, arquitetura em camadas (Aula09). "
        "Inclui o painel de gestao interno com chatbot (Claude Haiku) sobre um banco ficticio."
    ),
    version="1.1.0",
    lifespan=ciclo_de_vida,
)


def tratar_erro_de_negocio(request: Request, exc: ErroDeNegocioUsina | ErroDeNegocioDica) -> JSONResponse:
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


# Cada service define a propria classe ErroDeNegocio; as duas precisam de handler,
# senao a segunda importacao sobrescreve a primeira e os erros de usina viram 500.
app.add_exception_handler(ErroDeNegocioUsina, tratar_erro_de_negocio)
app.add_exception_handler(ErroDeNegocioDica, tratar_erro_de_negocio)

@app.exception_handler(StarletteHTTPException)
async def tratar_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Devolve {"error": {...}} puro quando o detail ja vem no formato padrao (painel/chatbot)."""
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail, headers=exc.headers)
    return await http_exception_handler(request, exc)


app.include_router(usina_router)
app.include_router(dica_router)
app.include_router(painel_router)
app.include_router(chatbot_router)

app.mount("/painel", StaticFiles(directory=PASTA_ESTATICA_PAINEL, html=True), name="painel")


@app.get("/", tags=["Status"])
def raiz() -> dict:
    return {"mensagem": "API no ar. Acesse /docs para o Swagger e /painel para o painel de gestao."}


@app.get("/painel", include_in_schema=False)
def redirecionar_painel() -> RedirectResponse:
    return RedirectResponse(url="/painel/")
