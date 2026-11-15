"""
Gera o contrato OpenAPI da API em docs/api/openapi.json.

Uso (na pasta backend/):
    python gerar_openapi.py

O teste tests/test_openapi.py falha se o arquivo estiver desatualizado,
entao rode este script sempre que mudar uma rota ou um schema.
"""

import json
from pathlib import Path

from app.main import app


DESTINO = Path(__file__).resolve().parent / "docs" / "api" / "openapi.json"


def gerar() -> str:
    """Contrato OpenAPI serializado (estavel entre execucoes)."""

    return json.dumps(app.openapi(), ensure_ascii=False, indent=2) + "\n"


def main() -> None:
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    DESTINO.write_text(gerar(), encoding="utf-8", newline="\n")
    print(f"OpenAPI gravado em {DESTINO}")


if __name__ == "__main__":
    main()
