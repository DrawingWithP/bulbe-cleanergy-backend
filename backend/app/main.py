"""
Ponto de entrada da aplicacao.
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.controllers.usina_controller import router as usina_router
from app.controllers.dica_controller import router as dica_router
from app.controllers.adesao_controller import router as adesao_router
from app.services.usina_service import ErroDeNegocio
from app.services.dica_service import ErroDeNegocio
from app.services.adesao_service import ErroDeNegocio
from app.controllers.simulacao_controller import router as simulacao_router
from app.controllers.indicacao_controller import router as indicacao_router

from app.services.usina_service import ErroDeNegocio
from app.services.dica_service import ErroDeNegocio
from app.services.simulacao_service import ErroDeNegocio

app = FastAPI(
    title="Bulbe Energia, API",
    description="Handson de CRUD em FastAPI, arquitetura em camadas (Aula09).",
    version="1.0.0",
    )
app.include_router(usina_router)
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

app.include_router(adesao_router)
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

app.include_router(dica_router)
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
app.include_router(simulacao_router)
app.include_router(indicacao_router)
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

@app.get("/", tags=["Status"])
def raiz() -> dict:
    return {"mensagem": "API no ar. Acesse /docs para o Swagger."}