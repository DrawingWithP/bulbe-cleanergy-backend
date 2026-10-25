"""
Ponto de entrada da aplicacao.
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.controllers.usina_controller import router as usina_router
from app.controllers.dica_controller import router as dica_router
from app.controllers.adesao_controller import router as adesao_router
from app.controllers.simulacao_controller import router as simulacao_router
from app.controllers.indicacao_controller import router as indicacao_router
from app.controllers.primeiro_acesso_controller import router as primeiro_acesso_router
from app.controllers.cliente_controller import router as cliente_router
from app.controllers.ativacao_controller import router as ativacao_router

from app.services.usina_service import ErroDeNegocio
from app.services.dica_service import ErroDeNegocio as DicaErroDeNegocio
from app.services.adesao_service import ErroDeNegocio as AdesaoErroDeNegocio
from app.services.simulacao_service import ErroDeNegocio as SimulacaoErroDeNegocio
from app.services.primeiro_acesso_service import ErroDeNegocio as PrimeiroAcessoErroDeNegocio
from app.services.cliente_service import ErroDeNegocio as ClienteErroDeNegocio
from app.services.ativacao_service import ErroDeNegocio as AtivacaoErroDeNegocio

app = FastAPI(
    title="Bulbe Energia, API",
    description="Handson de CRUD em FastAPI, arquitetura em camadas (Aula09).",
    version="1.0.0",
)

app.include_router(usina_router)
app.include_router(adesao_router)
app.include_router(dica_router)
app.include_router(simulacao_router)
app.include_router(indicacao_router)
app.include_router(primeiro_acesso_router)
app.include_router(cliente_router)
app.include_router(ativacao_router)


def _formatar_erro(exc) -> JSONResponse:
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


@app.exception_handler(ErroDeNegocio)
def tratar_erro_usina(request: Request, exc: ErroDeNegocio) -> JSONResponse:
    return _formatar_erro(exc)


@app.exception_handler(DicaErroDeNegocio)
def tratar_erro_dica(request: Request, exc: DicaErroDeNegocio) -> JSONResponse:
    return _formatar_erro(exc)


@app.exception_handler(AdesaoErroDeNegocio)
def tratar_erro_adesao(request: Request, exc: AdesaoErroDeNegocio) -> JSONResponse:
    return _formatar_erro(exc)


@app.exception_handler(SimulacaoErroDeNegocio)
def tratar_erro_simulacao(request: Request, exc: SimulacaoErroDeNegocio) -> JSONResponse:
    return _formatar_erro(exc)


@app.exception_handler(PrimeiroAcessoErroDeNegocio)
def tratar_erro_primeiro_acesso(request: Request, exc: PrimeiroAcessoErroDeNegocio) -> JSONResponse:
    return _formatar_erro(exc)


@app.exception_handler(ClienteErroDeNegocio)
def tratar_erro_cliente(request: Request, exc: ClienteErroDeNegocio) -> JSONResponse:
    return _formatar_erro(exc)


@app.exception_handler(AtivacaoErroDeNegocio)
def tratar_erro_ativacao(request: Request, exc: AtivacaoErroDeNegocio) -> JSONResponse:
    return _formatar_erro(exc)


@app.get("/", tags=["Status"])
def raiz() -> dict:
    return {"mensagem": "API no ar. Acesse /docs para o Swagger."}
