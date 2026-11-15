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

# Acrescimos da finalizacao (telas Entrar, Primeiro acesso, Abrir conta e
# Indicacoes): o CSS e o JS proprios e um unico bloco de telas, delimitado
# por comentarios. Fora disso, o HTML tem que ser identico ao original.
ACRESCIMOS_EXATOS = (
    b'  <link rel="stylesheet" href="telas.css">\n',
    b'  <script src="telas.js"></script>\n',
)

INICIO_BLOCO_TELAS = b"  <!-- BULBE-TELAS-NOVAS: inicio -->\n"
FIM_BLOCO_TELAS = b"  <!-- BULBE-TELAS-NOVAS: fim -->\n\n"


def remover_acrescimos(html: bytes) -> bytes:
    """
    Tira do HTML tudo o que foi acrescentado de proposito, cada item
    exatamente uma vez (um acrescimo repetido ou fora do lugar falha).
    """

    for trecho in (SCRIPTS_ADICIONADOS, *ACRESCIMOS_EXATOS):
        assert html.count(trecho) == 1, f"Acrescimo esperado uma vez: {trecho!r}"
        html = html.replace(trecho, b"")

    assert html.count(INICIO_BLOCO_TELAS) == 1 and html.count(FIM_BLOCO_TELAS) == 1, (
        "Bloco BULBE-TELAS-NOVAS ausente ou duplicado em final.html"
    )
    inicio = html.index(INICIO_BLOCO_TELAS)
    fim = html.index(FIM_BLOCO_TELAS) + len(FIM_BLOCO_TELAS)
    assert inicio < fim, "Bloco BULBE-TELAS-NOVAS fora de ordem"
    return html[:inicio] + html[fim:]


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
    permitindo apenas a inclusao de config.js e api.js
    e os acrescimos das telas novas (remover_acrescimos).
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

    html_sem_scripts = remover_acrescimos(
        html
    )

    digest_atual = hashlib.sha256(
        html_sem_scripts
    ).hexdigest()

    digest_esperado = manifesto["sha256"][
        "final.html"
    ]

    assert digest_atual == digest_esperado, (
        "final.html possui alteracoes alem "
        "dos acrescimos declarados (config.js, api.js "
        "e o bloco BULBE-TELAS-NOVAS)"
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
        "identicos; HTML original preservado "
        "(so os acrescimos declarados)"
    )


if __name__ == "__main__":
    main()
