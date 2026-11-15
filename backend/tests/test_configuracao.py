"""
Configuracao: chave secreta obrigatoria em producao.

Roda em um processo separado para nao reimportar a configuracao
da sessao de testes.
"""

import os
import subprocess
import sys
from pathlib import Path


BACKEND = Path(__file__).resolve().parents[1]


def _importar_config(**ambiente: str) -> subprocess.CompletedProcess:
    env = {
        **os.environ,
        "BULBE_SECRET_KEY": "",
        "BULBE_AMBIENTE": "",
        **ambiente,
    }

    return subprocess.run(
        [sys.executable, "-c", "import app.core.config as c; print(len(c.SECRET_KEY))"],
        cwd=BACKEND,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_producao_sem_chave_nao_inicia():
    resultado = _importar_config(BULBE_AMBIENTE="producao")
    assert resultado.returncode != 0
    assert "BULBE_SECRET_KEY" in resultado.stderr


def test_producao_com_chave_inicia():
    resultado = _importar_config(BULBE_AMBIENTE="producao", BULBE_SECRET_KEY="x" * 40)
    assert resultado.returncode == 0, resultado.stderr
    assert resultado.stdout.strip() == "40"


def test_desenvolvimento_sem_chave_usa_chave_local():
    resultado = _importar_config(BULBE_AMBIENTE="desenvolvimento")
    assert resultado.returncode == 0, resultado.stderr
    assert int(resultado.stdout.strip()) > 0
