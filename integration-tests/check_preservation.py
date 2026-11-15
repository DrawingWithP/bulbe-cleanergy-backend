"""
Verifica se o frontend original foi preservado: CSS/assets identicos (SHA-256)
e o HTML so com a inclusao de config.js e api.js.

Sem dependencias extras.

Historico: na revisao da integracao frontend-backend (commit base 86e8777) este
script tambem exigia que backend/migrations e sistema-de-gerenciamento/ ficassem
iguais ao commit base. Essa trava valia so para aquela revisao: depois dela, as
migrations e o sistema de gerenciamento evoluem normalmente (nova migration e
integracao do painel com o app), entao a verificacao foi retirada.
"""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

MANIFEST_PATH = Path(__file__).with_name(
    "frontend-source-sha256.json"
)

ARQUIVOS_IGNORADOS = {
    "final.html",
    "final.js",
}

SCRIPTS_ADICIONADOS = (
    b'  <script src="config.js"></script>\n'
    b'  <script src="api.js"></script>\n'
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

    print(
        "PASS: "
        f"{total_verificados} arquivos originais "
        "identicos; HTML somente adiciona scripts"
    )


if __name__ == "__main__":
    main()
