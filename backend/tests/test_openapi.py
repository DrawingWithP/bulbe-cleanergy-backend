"""
O contrato versionado em docs/api/openapi.json precisa refletir as rotas atuais.
"""

from gerar_openapi import DESTINO, gerar


def test_openapi_versionado_esta_atualizado():
    assert DESTINO.exists(), "Rode: python gerar_openapi.py"
    assert DESTINO.read_text(encoding="utf-8") == gerar(), (
        "docs/api/openapi.json esta desatualizado. Rode: python gerar_openapi.py"
    )
