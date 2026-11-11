"""
Jornadas reais: Chromium -> HTTP -> FastAPI -> SQLite temporário.

Sem mocks.

Executar:
    python integration-tests/test_browser.py

Opcionalmente, comparar o frontend com a versão original:
    python integration-tests/test_browser.py \
        --reference /caminho/frontend-original

Dependências de teste:
    playwright
    backend/requirements.txt

Instalação do navegador:
    playwright install chromium
"""

import argparse
import contextlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

from playwright.sync_api import (
    expect,
    sync_playwright,
)


ROOT = Path(__file__).resolve().parents[1]

CLIENTE_ID = (
    "8f1c2a6e-4b7d-4c1a-9f52-3d6a1b0c7e11"
)

CARTA_ID = (
    "a7c4e2b9-5d31-4f80-9e6b-8c2a1d4f7b55"
)

EMAIL_ADMIN = "admin@bulbe.com.br"
SENHA_ADMIN = "bulbe12345"


def obter_porta_livre() -> int:
    """
    Obtém uma porta TCP livre no endereço local.
    """

    with socket.socket() as servidor:
        servidor.bind(
            ("127.0.0.1", 0)
        )

        return servidor.getsockname()[1]


@contextlib.contextmanager
def executar_servidor(
    comando: list[str],
    diretorio: Path,
    ambiente: dict[str, str],
):
    """
    Executa um servidor durante o bloco de contexto
    e garante sua finalização ao término do teste.
    """

    with tempfile.TemporaryFile() as log:
        processo = subprocess.Popen(
            comando,
            cwd=diretorio,
            env=ambiente,
            stdout=log,
            stderr=log,
        )

        try:
            yield processo

        finally:
            if processo.poll() is None:
                processo.terminate()

                try:
                    processo.wait(timeout=10)

                except subprocess.TimeoutExpired:
                    processo.kill()
                    processo.wait(timeout=10)

            if processo.returncode not in {
                0,
                -15,
            }:
                log.seek(0)

                print(
                    log.read().decode(
                        errors="replace"
                    ),
                    file=sys.stderr,
                )


def aguardar_servidor(
    url: str,
    processo: subprocess.Popen,
) -> None:
    """
    Aguarda o servidor responder antes
    de iniciar os testes.
    """

    for _ in range(200):
        try:
            with urllib.request.urlopen(
                url,
                timeout=1,
            ):
                return

        except Exception:
            if processo.poll() is not None:
                raise RuntimeError(
                    "Servidor terminou antes de iniciar."
                )

            time.sleep(0.1)

    raise RuntimeError(
        "Servidor não iniciou dentro do tempo esperado."
    )


def preparar_banco(
    ambiente: dict[str, str],
) -> None:
    """
    Cria as tabelas e executa o seed
    no banco SQLite temporário.
    """

    codigo = (
        "from app.db import models; "
        "from app.db.database import Base, engine, SessionLocal; "
        "from app.db.seed import popular; "
        "Base.metadata.create_all(engine); "
        "session = SessionLocal(); "
        "popular(session); "
        "session.close()"
    )

    subprocess.run(
        [
            sys.executable,
            "-c",
            codigo,
        ],
        cwd=ROOT / "backend",
        env=ambiente,
        check=True,
    )


def autenticar(
    api,
    endereco: str,
) -> dict[str, str]:
    """
    Realiza login e devolve o cabeçalho
    Authorization para chamadas protegidas.
    """

    resposta = api.post(
        f"{endereco}/v1/auth/login",
        form={
            "username": EMAIL_ADMIN,
            "password": SENHA_ADMIN,
        },
    )

    assert resposta.status == 200, (
        resposta.status,
        resposta.text(),
    )

    token = resposta.json()["access_token"]

    return {
        "Authorization": f"Bearer {token}"
    }


def executar(
    reference: Path | None,
) -> None:
    """
    Executa as jornadas integradas do frontend
    contra o backend e banco reais.
    """

    with tempfile.TemporaryDirectory(
        prefix="bulbe-integration-"
    ) as diretorio_temporario:
        banco = (
            Path(diretorio_temporario)
            / "test.db"
        )

        ambiente = {
            **os.environ,
            "BULBE_DATABASE_URL": (
                f"sqlite:///{banco}"
            ),
            "BULBE_SECRET_KEY": (
                "isolated-integration-test-key-only"
            ),
            "BULBE_FRONTEND_CLIENTE_ID": CLIENTE_ID,
        }

        preparar_banco(ambiente)

        porta = obter_porta_livre()
        endereco = f"http://127.0.0.1:{porta}"

        comando_backend = [
            sys.executable,
            "-m",
            "uvicorn",
            "dev_frontend:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(porta),
        ]

        with executar_servidor(
            comando_backend,
            ROOT / "backend",
            ambiente,
        ) as processo:
            aguardar_servidor(
                f"{endereco}/",
                processo,
            )

            with sync_playwright() as playwright:
                navegador = playwright.chromium.launch()

                pagina = navegador.new_page(
                    viewport={
                        "width": 430,
                        "height": 932,
                    },
                    device_scale_factor=1,
                )

                erros: list[str] = []
                dialogos: list[str] = []
                requisicoes: list[
                    tuple[str, str, str | None]
                ] = []

                pagina.on(
                    "pageerror",
                    lambda erro: erros.append(
                        str(erro)
                    ),
                )

                pagina.on(
                    "dialog",
                    lambda dialogo: (
                        dialogos.append(
                            dialogo.message
                        ),
                        dialogo.dismiss(),
                    ),
                )

                pagina.on(
                    "request",
                    lambda requisicao: requisicoes.append(
                        (
                            requisicao.method,
                            requisicao.url,
                            requisicao.post_data,
                        )
                    ),
                )

                pagina.goto(
                    f"{endereco}/frontend/final.html"
                )

                pagina.wait_for_timeout(600)

                assert not erros, erros

                if reference:
                    porta_original = obter_porta_livre()

                    endereco_original = (
                        f"http://127.0.0.1:{porta_original}"
                    )

                    comando_original = [
                        sys.executable,
                        "-m",
                        "http.server",
                        str(porta_original),
                        "--bind",
                        "127.0.0.1",
                    ]

                    with executar_servidor(
                        comando_original,
                        reference,
                        ambiente,
                    ) as processo_referencia:
                        aguardar_servidor(
                            (
                                f"{endereco_original}"
                                "/final.html"
                            ),
                            processo_referencia,
                        )

                        pagina_original = navegador.new_page(
                            viewport={
                                "width": 430,
                                "height": 932,
                            },
                            device_scale_factor=1,
                        )

                        pagina_original.goto(
                            (
                                f"{endereco_original}"
                                "/final.html"
                            )
                        )

                        pagina_original.wait_for_timeout(
                            600
                        )

                        assert (
                            pagina.screenshot()
                            == pagina_original.screenshot()
                        ), (
                            "Tela inicial mudou visualmente."
                        )

                        pagina_original.close()

                    print(
                        "PASS: screenshot da tela inicial "
                        "idêntica ao original"
                    )

                api = pagina.request

                assert api.get(
                    f"{endereco}/"
                ).status == 200

                assert api.get(
                    f"{endereco}/v1/auth/me"
                ).status == 401

                login_invalido = api.post(
                    f"{endereco}/v1/auth/login",
                    form={
                        "username": (
                            "missing@example.test"
                        ),
                        "password": "bad",
                    },
                )

                assert login_invalido.status == 401

                headers_autenticacao = autenticar(
                    api,
                    endereco,
                )

                usuario_atual = api.get(
                    f"{endereco}/v1/auth/me",
                    headers=headers_autenticacao,
                )

                assert usuario_atual.status == 200

                print(
                    "PASS: inicialização e autenticação "
                    "real (200/401)"
                )

                pagina.locator(
                    ".primary-button"
                ).click()

                expect(
                    pagina.locator(
                        "#st-progresso-pct"
                    )
                ).to_have_text("30%")

                pagina.locator(
                    ".st-jornada-detalhes"
                ).click()

                expect(
                    pagina.locator(
                        "#det-numero-etapa"
                    )
                ).to_have_text("2")

                expect(
                    pagina.locator(
                        "#det-status-titulo"
                    )
                ).not_to_have_text("—")

                pagina.locator(
                    "#screen-detalhes [data-nav-back]"
                ).click()

                pagina.locator(
                    (
                        '#screen-status '
                        '[data-nav="screen-dicas"]'
                    )
                ).click()

                expect(
                    pagina.locator(
                        "#dc-dicas-list li"
                    )
                ).to_have_count(2)

                expect(
                    pagina.locator(
                        ".dc-mensal span"
                    )
                ).to_have_text("R$ 12,50")

                pagina.locator(
                    "#dc-dicas-indicators li"
                ).nth(1).click()

                expect(
                    pagina.locator(
                        ".dc-mensal span"
                    )
                ).to_have_text("R$ 25,00")

                print(
                    "PASS: status, detalhes, dicas e "
                    "carrossel com dados da API"
                )

                pagina.locator(
                    (
                        '#screen-dicas '
                        '[data-nav="screen-vantagens"]'
                    )
                ).click()

                expect(
                    pagina.locator(
                        "#van-titulo-dias"
                    )
                ).to_have_text(
                    "Sua carta chegou! ✨"
                )

                expect(
                    pagina.locator(
                        ".van-lista-parceiros li"
                    )
                ).to_have_count(3)

                pagina.locator(
                    "#van-card-proxima-carta"
                ).click()

                pagina.locator(
                    "#carta-btn-abrir"
                ).click()

                expect(
                    pagina.locator(
                        "#rc-titulo"
                    )
                ).to_have_text(
                    "500 pontos Livelo"
                )

                codigo_cupom = pagina.locator(
                    "#rc-cupom-codigo"
                ).inner_text()

                pagina.locator(
                    "#rc-btn-salvar"
                ).click()

                expect(
                    pagina.locator(
                        "#screen-vantagens"
                    )
                ).to_have_class(
                    "screen active",
                    timeout=10000,
                )

                resposta_cupons = api.get(
                    (
                        f"{endereco}/v1/clientes/"
                        f"{CLIENTE_ID}/cupons"
                    )
                )

                assert resposta_cupons.status == 200

                cupons = resposta_cupons.json()[
                    "data"
                ]

                cupom_gerado = next(
                    cupom
                    for cupom in cupons
                    if cupom["codigo"] == codigo_cupom
                )

                assert (
                    cupom_gerado["situacao"]
                    == "salvo"
                )

                pagina.reload()

                pagina.locator(
                    ".primary-button"
                ).click()

                pagina.locator(
                    (
                        '#screen-status '
                        '[data-nav="screen-vantagens"]'
                    )
                ).click()

                expect(
                    pagina.locator(
                        "#van-container-cupons"
                    )
                ).to_contain_text(
                    "500 pontos Livelo"
                )

                resultado_abertura = api.post(
                    (
                        f"{endereco}/v1/cartas/"
                        f"{CARTA_ID}/abertura"
                    )
                )

                assert resultado_abertura.status in {
                    200,
                    201,
                }

                assert (
                    resultado_abertura.json()[
                        "cupom"
                    ]["id"]
                    == cupom_gerado["id"]
                )

                pagina.locator(
                    "#van-container-cupons li"
                ).filter(
                    has_text="500 pontos Livelo"
                ).click()

                expect(
                    pagina.locator(
                        "#rc-cupom-codigo"
                    )
                ).to_have_text(codigo_cupom)

                pagina.locator(
                    "#rc-btn-copiar"
                ).click()

                expect(
                    pagina.locator(
                        "#rc-btn-copiar"
                    )
                ).to_have_text("Copiado!")

                print(
                    "PASS: carta, resgate, cupom salvo "
                    "e persistência após recarregar; "
                    "abertura idempotente"
                )

                simuladores = [
                    (
                        "screen-simulador",
                        "sim",
                    ),
                    (
                        "screen-simulador-logado",
                        "slog",
                    ),
                ]

                for tela, prefixo in simuladores:
                    pagina.evaluate(
                        "(id) => navigateTo(id)",
                        tela,
                    )

                    pagina.wait_for_timeout(350)

                    pagina.locator(
                        f"#{prefixo}-vlr-pago"
                    ).fill("200")

                    pagina.locator(
                        f"#{prefixo}-vlr-pago"
                    ).blur()

                    pagina.wait_for_timeout(800)

                    expect(
                        pagina.locator(
                            (
                                f"#{prefixo}"
                                "-economia-total"
                            )
                        )
                    ).to_have_text("90")

                    pagina.locator(
                        f"#{tela} .sim-btn-mais"
                    ).click()

                    expect(
                        pagina.locator(
                            (
                                f"#{prefixo}"
                                "-economia-total"
                            )
                        )
                    ).to_have_text("140")

                    pagina.locator(
                        f"#{tela} .sim-pill"
                    ).nth(2).click()

                    expect(
                        pagina.locator(
                            (
                                f"#{prefixo}"
                                "-economia-total"
                            )
                        )
                    ).to_have_text("410")

                    pagina.locator(
                        (
                            f"#{prefixo}"
                            "-custom-principal"
                        )
                    ).click()

                    pagina.locator(
                        (
                            f"#{prefixo}"
                            "-custom-meses"
                        )
                    ).fill("2")

                    pagina.locator(
                        f"#{tela} .sim-btn-ok"
                    ).click()

                    expect(
                        pagina.locator(
                            (
                                f"#{prefixo}"
                                "-economia-total"
                            )
                        )
                    ).to_have_text("110")

                print(
                    "PASS: dois simuladores, períodos, "
                    "zero ou mais indicações e "
                    "persistência real"
                )

                pagina_cliente_inexistente = (
                    navegador.new_page()
                )

                pagina_cliente_inexistente.on(
                    "dialog",
                    lambda dialogo: (
                        dialogos.append(
                            dialogo.message
                        ),
                        dialogo.dismiss(),
                    ),
                )

                pagina_cliente_inexistente.goto(
                    f"{endereco}/frontend/final.html"
                )

                pagina_cliente_inexistente.evaluate(
                    """
                    window.BULBE_CONFIG.clienteId =
                        "inexistente"
                    """
                )

                pagina_cliente_inexistente.locator(
                    ".primary-button"
                ).click()

                expect(
                    pagina_cliente_inexistente.locator(
                        "#st-progresso-pct"
                    )
                ).to_have_text("—")

                pagina_cliente_inexistente.wait_for_timeout(
                    800
                )

                assert any(
                    "não foi encontrado" in dialogo
                    for dialogo in dialogos
                ), dialogos

                assert not erros, erros

                assert any(
                    "/v1/simulacoes" in url
                    for _, url, _ in requisicoes
                )

                codigo_validacao_banco = (
                    "from sqlalchemy import select; "
                    "from app.db.database import SessionLocal; "
                    "from app.db.models import "
                    "SimulacaoModel, CupomModel; "
                    "session = SessionLocal(); "
                    "assert len("
                    "session.scalars("
                    "select(SimulacaoModel)"
                    ").all()) >= 6; "
                    f'assert session.get(CupomModel, '
                    f'"{cupom_gerado["id"]}")'
                    '.situacao == "salvo"; '
                    "session.close()"
                )

                subprocess.run(
                    [
                        sys.executable,
                        "-c",
                        codigo_validacao_banco,
                    ],
                    cwd=ROOT / "backend",
                    env=ambiente,
                    check=True,
                )

                assert all(
                    url.startswith(
                        f"{endereco}/"
                    )
                    for _, url, _ in requisicoes
                    if "/v1/" in url
                )

                erro_json = pagina.evaluate(
                    """
                    async () => {
                        try {
                            await BulbeAPI.request(
                                "/frontend/final.html"
                            );
                            return "";
                        } catch (erro) {
                            return erro.message;
                        }
                    }
                    """
                )

                assert "JSON inválida" in erro_json

                print(
                    "PASS: 404, persistência SQL de "
                    "simulações/cupons, nenhum erro "
                    "JavaScript ou CORS"
                )

                processo.terminate()
                processo.wait(timeout=10)

                pagina.evaluate(
                    "() => window._onAtivacao()"
                )

                expect(
                    pagina.locator(
                        "#st-progresso-pct"
                    )
                ).to_have_text("—")

                assert any(
                    "Não foi possível comunicar"
                    in dialogo
                    for dialogo in dialogos
                )

                print(
                    "PASS: servidor indisponível e "
                    "JSON inválido, sem sucesso simulado"
                )

                pagina_cliente_inexistente.close()
                navegador.close()

        with executar_servidor(
            comando_backend,
            ROOT / "backend",
            ambiente,
        ) as processo:
            aguardar_servidor(
                f"{endereco}/",
                processo,
            )

            with urllib.request.urlopen(
                (
                    f"{endereco}/v1/cupons/"
                    f"{cupom_gerado['id']}"
                )
            ) as resposta:
                cupom_salvo = json.load(
                    resposta
                )

            assert (
                cupom_salvo["situacao"]
                == "salvo"
            )

        print(
            "PASS: persistência após reiniciar "
            "o backend"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--reference",
        type=Path,
    )

    argumentos = parser.parse_args()

    executar(argumentos.reference)
