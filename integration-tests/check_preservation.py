"""
Verifica CSS/assets originais, HTML e escopo preservado.

Sem dependencias extras.
"""

import hashlib
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]

MANIFEST_PATH = Path(__file__).with_name(
    "frontend-source-sha256.json"
)

COMMIT_BASE = "86e8777040bb7733e13d3c325c5bd2c3de49d099"

ARQUIVOS_IGNORADOS = {
    "final.html",
    "final.js",
}

SCRIPTS_ADICIONADOS = (
    b'  <script src="config.js"></script>\n'
    b'  <script src="api.js"></script>\n'
)

ESCOPO_PRESERVADO = (
    "backend/migrations",
    "sistema-de-gerenciamento",
)


def calcular_sha256(
    caminho: Path,
) -> str:
    """
    Calcula o SHA-256 de um arquivo.
    """

    return hashlib.sha256(
        caminho.read_bytes()
    ).hexdigest()


def carregar_manifesto() -> dict:
    """
    Carrega o manifesto com os hashes
    dos arquivos originais.
    """

    return json.loads(
        MANIFEST_PATH.read_text(
            encoding="utf-8"
        )
    )


def verificar_arquivos_originais(
    manifesto: dict,
) -> int:
    """
    Verifica se CSS e assets permanecem
    identicos aos arquivos originais.

    final.html e final.js sao tratados
    separadamente porque fazem parte
    da integracao.
    """

    total_verificados = 0

    for nome, digest_esperado in manifesto[
        "sha256"
    ].items():
        if nome in ARQUIVOS_IGNORADOS:
            continue

        caminho = ROOT / "frontend" / nome

        assert caminho.exists(), (
            f"Arquivo nao encontrado: {caminho}"
        )

        digest_atual = calcular_sha256(
            caminho
        )

        assert digest_atual == digest_esperado, (
            f"Arquivo original alterado: {nome}"
        )

        total_verificados += 1

    return total_verificados


def verificar_html(
    manifesto: dict,
) -> None:
    """
    Confirma que o HTML original foi preservado,
    permitindo apenas a inclusao dos scripts
    config.js e api.js.
    """

    caminho_html = (
        ROOT
        / "frontend"
        / "final.html"
    )

    assert caminho_html.exists(), (
        f"Arquivo nao encontrado: {caminho_html}"
    )

    html = caminho_html.read_bytes()

    html_sem_scripts = html.replace(
        SCRIPTS_ADICIONADOS,
        b"",
    )

    digest_atual = hashlib.sha256(
        html_sem_scripts
    ).hexdigest()

    digest_esperado = manifesto["sha256"][
        "final.html"
    ]

    assert digest_atual == digest_esperado, (
        "final.html possui alteracoes alem "
        "da inclusao de config.js e api.js"
    )


def verificar_escopo_preservado() -> None:
    """
    Confirma que migrations e o sistema independente
    permanecem iguais ao commit base.

    backend/app nao faz parte desta verificacao porque
    contem alteracoes intencionais da integracao.
    """

    comando = [
        "git",
        "diff",
        COMMIT_BASE,
        "--name-only",
        "--",
        *ESCOPO_PRESERVADO,
    ]

    resultado = subprocess.run(
        comando,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    arquivos_alterados = (
        resultado.stdout.strip()
    )

    assert not arquivos_alterados, (
        "Foram encontradas alteracoes no "
        "escopo que deveria permanecer preservado:\n"
        f"{arquivos_alterados}"
    )


def main() -> None:
    """
    Executa todas as verificacoes.
    """

    manifesto = carregar_manifesto()

    total_verificados = (
        verificar_arquivos_originais(
            manifesto
        )
    )

    verificar_html(
        manifesto
    )

    verificar_escopo_preservado()

    print(
        "PASS: "
        f"{total_verificados} arquivos originais "
        "identicos; HTML somente adiciona scripts; "
        "migrations e sistema independente preservados"
    )


if __name__ == "__main__":
    main()
