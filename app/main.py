"""
Ponto de entrada da aplicacao.
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.controllers.usina_controller import router as usina_router
from app.services.usina_service import ErroDeNegocio

app = FastAPI(
    title="Bulbe Energia, API de Usinas",
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

@app.get("/", tags=["Status"])
def raiz() -> dict:
    return {"mensagem": "API de Usinas no ar. Acesse /docs para o Swagger."}