"""
Teste de ponta a ponta entre o app (backend) e o sistema de gerenciamento.

1. Cria o banco do app num diretorio temporario com as migrations reais e o seed.
2. Sobe a API do app (uvicorn, so em loopback) e usa a jornada do app por HTTP:
   simulacao logada, indicacao e abertura de carta.
3. No sistema de gerenciamento (banco proprio, temporario): sincroniza com o app e confere
   que o painel ve o que o app gravou.
4. Pelo painel, altera a etapa de ativacao do cliente e confere na API do app que mudou.

Sem mocks. Nada fora do diretorio temporario e alterado.

Uso (na raiz do repositorio):
    python integration-tests/test_sistemas_integrados.py

O Python precisa das dependencias das duas partes (requirements.txt da raiz). Para usar
ambientes separados: PYTHON_BACKEND=backend/venv/Scripts/python.exe
PYTHON_PAINEL=sistema-de-gerenciamento/.venv/Scripts/python.exe
"""
import json
import os
import socket
import subprocess
import sys
import tempfile
import textwrap
import time
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
BACKEND = RAIZ / "backend"
PAINEL = RAIZ / "sistema-de-gerenciamento"

ID_MARCOS = "8f1c2a6e-4b7d-4c1a-9f52-3d6a1b0c7e11"
ID_CARTA_MARCOS = "a7c4e2b9-5d31-4f80-9e6b-8c2a1d4f7b55"


def _python(variavel: str) -> str:
    valor = os.environ.get(variavel)
    return str((RAIZ / valor).resolve()) if valor and not Path(valor).is_absolute() else (valor or sys.executable)


def _porta_livre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _http(metodo: str, url: str, corpo: dict | None = None) -> tuple[int, dict]:
    dados = json.dumps(corpo).encode() if corpo is not None else None
    requisicao = urllib.request.Request(url, data=dados, method=metodo,
                                        headers={"Content-Type": "application/json", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(requisicao, timeout=15) as resposta:
            return resposta.status, json.loads(resposta.read() or b"{}")
    except urllib.error.HTTPError as erro:
        return erro.code, json.loads(erro.read() or b"{}")


def _esperar(url: str, processo: subprocess.Popen, segundos: int = 60) -> None:
    limite = time.time() + segundos
    while time.time() < limite:
        if processo.poll() is not None:
            raise AssertionError("A API do app encerrou antes de responder.")
        try:
            urllib.request.urlopen(url, timeout=2)
            return
        except OSError:
            time.sleep(0.3)
    raise AssertionError(f"A API do app nao respondeu em {segundos} s.")


SCRIPT_PAINEL = textwrap.dedent('''
    import json, sys
    from fastapi.testclient import TestClient
    from app.database.conexao import inicializar_banco
    from app.database import consultas
    from app.integracao import sincronizacao
    from app.painel.auth import criar_token
    from app.main import app

    inicializar_banco(recriar=True)
    resultado = sincronizacao.sincronizar()
    assert resultado["sucesso"], resultado

    marcos = [c for c in consultas.buscar_clientes("Marcos Andrade", limite=10) if c["nome"] == "Marcos Andrade"]
    assert len(marcos) == 1, marcos
    cliente = consultas.obter_cliente(marcos[0]["id"])
    assert cliente["id_app"] == sys.argv[1], cliente
    indicacoes = consultas.listar_indicacoes(cliente["id"])["data"]
    assert any(i["nome_indicado"] == "Indicada Pelo App" for i in indicacoes), indicacoes
    cupons = consultas.listar_cupons(cliente["id"])
    assert any(c["codigo"] for c in cupons), cupons

    admin = consultas.obter_funcionario_por_email("admin@bulbe.com.br")
    with TestClient(app) as http:
        resposta = http.patch(
            f"/v1/painel/clientes/{cliente['id']}/ativacao",
            json={"etapa_atual": 3, "observacao": "Alterado pelo teste integrado"},
            headers={"Authorization": "Bearer " + criar_token(admin)},
        )
        assert resposta.status_code == 200, resposta.text
        assert resposta.json()["ativacao"]["etapa_atual"] == 3, resposta.json()
    print(json.dumps({"contagens": resultado["contagens"]}))
''')


def main() -> None:
    python_backend = _python("PYTHON_BACKEND")
    python_painel = _python("PYTHON_PAINEL")

    # ignore_cleanup_errors: no Windows o SQLite pode ficar preso por um instante depois do processo sair.
    with tempfile.TemporaryDirectory(prefix="bulbe-integrado-", ignore_cleanup_errors=True) as pasta:
        pasta = Path(pasta)
        url_app = "sqlite:///" + (pasta / "app.db").as_posix()
        url_painel = "sqlite:///" + (pasta / "painel.db").as_posix()
        porta = _porta_livre()
        base = f"http://127.0.0.1:{porta}"

        env_backend = {**os.environ, "BULBE_DATABASE_URL": url_app,
                       "BULBE_SECRET_KEY": "chave-do-teste-integrado-0123456789abcdef"}
        subprocess.run([python_backend, "-m", "alembic", "upgrade", "head"], cwd=BACKEND, env=env_backend,
                       check=True, capture_output=True)
        subprocess.run([python_backend, "-m", "app.db.seed"], cwd=BACKEND, env=env_backend, check=True,
                       capture_output=True)

        api = subprocess.Popen(
            [python_backend, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(porta)],
            cwd=BACKEND, env=env_backend, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        try:
            _esperar(base + "/", api)

            # Jornada no app
            status, simulacao = _http("POST", base + "/v1/simulacoes", {
                "valor_atual": 250, "valor_proposto": 212.5, "periodo_meses": 12, "indicacoes": 1,
                "cliente_id": ID_MARCOS,
            })
            assert status == 201 and simulacao["economia_total"] == 500.0, simulacao
            status, indicacao = _http("POST", base + "/v1/indicacoes", {
                "cliente_id": ID_MARCOS, "nome": "Indicada Pelo App", "contato": "indicada@exemplo.com",
            })
            assert status == 201, indicacao
            status, abertura = _http("POST", f"{base}/v1/cartas/{ID_CARTA_MARCOS}/abertura")
            assert status == 201, abertura

            # Painel: sincroniza e altera a etapa pela API do app
            env_painel = {
                **os.environ,
                "BULBE_DB_URL": url_painel,
                "INTEGRACAO_APP_DB_URL": url_app,
                "INTEGRACAO_INTERVALO_SEGUNDOS": "0",
                "INTEGRACAO_APP_API_URL": base,
                "ANTHROPIC_API_KEY": "",
                "PAINEL_SECRET": "segredo-do-teste-integrado-0123456789abcdef",
                "PAINEL_SENHA_DEMO": "senha-do-teste-integrado",
                "SMTP_HOST": "",
            }
            painel = subprocess.run([python_painel, "-c", SCRIPT_PAINEL, ID_MARCOS], cwd=PAINEL, env=env_painel,
                                    capture_output=True, text=True, timeout=180)
            assert painel.returncode == 0, painel.stdout + painel.stderr

            # O app ve a etapa alterada pelo painel
            status, ativacao = _http("GET", f"{base}/v1/clientes/{ID_MARCOS}/ativacao")
            assert status == 200 and ativacao["etapa_atual"] == 3, ativacao
        finally:
            api.terminate()
            try:
                api.wait(timeout=10)
            except subprocess.TimeoutExpired:
                api.kill()

    print("PASS: app e sistema de gerenciamento integrados (sincronizacao app -> painel e etapa painel -> app)")


if __name__ == "__main__":
    main()
