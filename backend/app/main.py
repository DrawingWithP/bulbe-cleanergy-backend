"""
Ponto de entrada da aplicacao.
"""

from importlib import import_module

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


# Cada modulo tem um controller (app/controllers/<nome>_controller.py) e um
# servico com a propria classe ErroDeNegocio (app/services/<nome>_service.py).
# Um modulo novo so precisa entrar nesta lista.
MODULOS = (
    "auth",
    "usina",
    "adesao",
    "dica",
    "simulacao",
    "indicacao",
    "primeiro_acesso",
    "cliente",
    "ativacao",
    "parceiro",
    "cupom",
    "carta",
    "bandeira",
    "demonstracao",
    "cupom_catalogo",
)

# Modulos cujo servico declara ErroDeNegocio (auth usa o de usina).
MODULOS_COM_ERRO = tuple(modulo for modulo in MODULOS if modulo != "auth")


app = FastAPI(
    title="Bulbe Energia, API",
    description=(
        "API do app da Bulbe Energia (squad Cleanergy): clientes, adesao, "
        "primeiro acesso, jornada de ativacao, simulador com bandeira "
        "tarifaria, indicacoes, Clube Bulbe (cartas e cupons), parceiros, "
        "dicas, usinas e relogio de demonstracao. Arquitetura em camadas, "
        "SQLAlchemy/Alembic e autenticacao JWT para operadores."
    ),
    version="1.2.0",
)


for modulo in MODULOS:
    app.include_router(
        import_module(f"app.controllers.{modulo}_controller").router
    )


def _formatar_erro(request: Request, exc) -> JSONResponse:
    """
    Formata os erros de negocio no padrao da API:
    {"error": {"code", "message", "status"}}.
    """

    headers = (
        {"WWW-Authenticate": "Bearer"}
        if exc.status == 401
        else None
    )

    return JSONResponse(
        status_code=exc.status,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "status": exc.status,
            }
        },
        headers=headers,
    )


for modulo in MODULOS_COM_ERRO:
    app.add_exception_handler(
        import_module(f"app.services.{modulo}_service").ErroDeNegocio,
        _formatar_erro,
    )


@app.get(
    "/",
    tags=["Status"],
)
def raiz() -> dict:
    return {
        "mensagem": (
            "API no ar. Acesse /docs para o Swagger."
        )
    }
