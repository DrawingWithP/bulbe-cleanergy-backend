"""
Entrada opcional de desenvolvimento:
API e frontend na mesma origem, sem alterar app.main.
"""

import json
import os
from pathlib import Path

from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from app.main import app


FRONTEND_DIR = (
    Path(__file__).resolve().parents[1]
    / "frontend"
)


@app.get(
    "/frontend/config.js",
    include_in_schema=False,
)
def frontend_config() -> Response:
    """
    Fornece a configuracao do frontend
    durante a execucao local.
    """

    config = {
        "apiBase": "",
        "clienteId": os.getenv(
            "BULBE_FRONTEND_CLIENTE_ID"
        ),
    }

    conteudo = (
        "window.BULBE_CONFIG = "
        + json.dumps(config)
        + ";"
    )

    return Response(
        content=conteudo,
        media_type="application/javascript",
        headers={
            "Cache-Control": "no-store",
        },
    )


app.mount(
    "/frontend",
    StaticFiles(
        directory=FRONTEND_DIR
    ),
    name="frontend",
)
