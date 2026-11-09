"""Entrada opcional de desenvolvimento: API e frontend na mesma origem, sem alterar app.main."""
import json
import os
from pathlib import Path
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from app.main import app


@app.get('/frontend/config.js', include_in_schema=False)
def frontend_config():
    config = {'apiBase': '', 'clienteId': os.getenv('BULBE_FRONTEND_CLIENTE_ID')}
    return Response('window.BULBE_CONFIG = ' + json.dumps(config) + ';',
                    media_type='application/javascript', headers={'Cache-Control': 'no-store'})


app.mount('/frontend', StaticFiles(directory=Path(__file__).resolve().parents[1] / 'frontend'), name='frontend')
