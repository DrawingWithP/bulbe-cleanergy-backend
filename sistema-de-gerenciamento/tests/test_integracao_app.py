"""
Integracao com o app (backend): sincronizacao app -> painel e alteracao de etapa painel -> app.

O banco do app e um SQLite temporario com o mesmo esquema das migrations do backend
(a verificacao com o backend de verdade fica em integration-tests/test_sistemas_integrados.py).
A API do app e simulada por um servidor HTTP local que grava nesse mesmo SQLite.

Estes testes alteram o banco do painel (vinculam e criam clientes); no fim do modulo o banco de
teste e recriado, para os outros arquivos continuarem vendo o estado inicial do seed.
"""
import hashlib
import json
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from app.database import conexao, consultas
from app.integracao import api_app, sincronizacao

ESQUEMA_APP = """
CREATE TABLE usinas (id INTEGER PRIMARY KEY, nome VARCHAR(100) NOT NULL, localizacao VARCHAR(100) NOT NULL,
    capacidade_geracao_kwh FLOAT NOT NULL, status VARCHAR(20) NOT NULL, data_ativacao DATE NOT NULL);
CREATE TABLE parceiros (id VARCHAR(36) PRIMARY KEY, nome VARCHAR(100) NOT NULL, categoria VARCHAR(60) NOT NULL,
    logo_url VARCHAR(255), ativo BOOLEAN NOT NULL, criado_em VARCHAR(30) NOT NULL, atualizado_em VARCHAR(30));
CREATE TABLE dicas (id INTEGER PRIMARY KEY, titulo VARCHAR(100) NOT NULL, descricao VARCHAR(250) NOT NULL,
    economia FLOAT NOT NULL, imagem_svg TEXT NOT NULL, data_ativacao DATE NOT NULL);
CREATE TABLE clientes (id VARCHAR(36) PRIMARY KEY, nome VARCHAR(120) NOT NULL, email VARCHAR(255) NOT NULL,
    cpf VARCHAR(11) NOT NULL, telefone VARCHAR(20) NOT NULL, cep VARCHAR(10) NOT NULL,
    logradouro VARCHAR(150) NOT NULL, numero VARCHAR(20) NOT NULL, complemento VARCHAR(100),
    bairro VARCHAR(100) NOT NULL, cidade VARCHAR(100) NOT NULL, uf VARCHAR(2) NOT NULL,
    distribuidora VARCHAR(50) NOT NULL, numero_instalacao VARCHAR(30) NOT NULL, status VARCHAR(20) NOT NULL,
    acesso_habilitado BOOLEAN NOT NULL, criado_em VARCHAR(30) NOT NULL);
CREATE TABLE ativacoes (cliente_id VARCHAR(36) PRIMARY KEY, etapa_atual INTEGER NOT NULL,
    distribuidora VARCHAR(50) NOT NULL, prazo_ativacao_dias INTEGER NOT NULL,
    previsao_conclusao VARCHAR(10) NOT NULL, atualizado_em VARCHAR(30) NOT NULL, observacoes JSON NOT NULL);
CREATE TABLE ofensivas_clube (cliente_id VARCHAR(36) PRIMARY KEY, semanas_sequencia INTEGER NOT NULL);
CREATE TABLE cartas (id VARCHAR(36) PRIMARY KEY, cliente_id VARCHAR(36) NOT NULL, semana INTEGER NOT NULL,
    tipo VARCHAR(20) NOT NULL, situacao VARCHAR(20) NOT NULL, disponivel_em VARCHAR(30) NOT NULL,
    aberta_em VARCHAR(30), cupom_id VARCHAR(36));
CREATE TABLE cupons (id VARCHAR(36) PRIMARY KEY, cliente_id VARCHAR(36) NOT NULL, carta_id VARCHAR(36),
    tag VARCHAR(60) NOT NULL, titulo VARCHAR(120) NOT NULL, descricao VARCHAR(300) NOT NULL,
    codigo VARCHAR(30) NOT NULL, parceiro_id VARCHAR(36) NOT NULL, parceiro_nome VARCHAR(100) NOT NULL,
    parceiro_categoria VARCHAR(60) NOT NULL, situacao VARCHAR(20) NOT NULL, valido_ate VARCHAR(10) NOT NULL,
    dias_restantes INTEGER NOT NULL, criado_em VARCHAR(30) NOT NULL, usado_em VARCHAR(30));
CREATE TABLE indicacoes (id INTEGER PRIMARY KEY, cliente_id VARCHAR(36) NOT NULL, nome VARCHAR(100) NOT NULL,
    contato VARCHAR(100) NOT NULL, situacao VARCHAR(20) NOT NULL, bonus FLOAT NOT NULL);
CREATE TABLE simulacoes (id INTEGER PRIMARY KEY, valor_atual FLOAT NOT NULL, valor_proposto FLOAT NOT NULL,
    periodo_meses INTEGER NOT NULL, indicacoes INTEGER NOT NULL, data_ativacao DATE NOT NULL,
    cliente_id VARCHAR(36), bandeira VARCHAR(20) DEFAULT 'verde' NOT NULL, economia_mensal FLOAT,
    economia_total FLOAT);
CREATE TABLE adesoes (id INTEGER PRIMARY KEY, nome VARCHAR(100) NOT NULL, email VARCHAR(100) NOT NULL,
    cpf VARCHAR(11) NOT NULL, telefone VARCHAR(12) NOT NULL, cep VARCHAR(8) NOT NULL,
    logradouro VARCHAR(100) NOT NULL, numero INTEGER NOT NULL, bairro VARCHAR(40) NOT NULL,
    cidade VARCHAR(40) NOT NULL, uf VARCHAR(2) NOT NULL, distribuidora VARCHAR(15) NOT NULL,
    numero_instalacao VARCHAR(30) NOT NULL, valor_conta_atual FLOAT NOT NULL, status VARCHAR(20) NOT NULL,
    data_ativacao DATE NOT NULL);
"""

ID_MARCOS_APP = "8f1c2a6e-4b7d-4c1a-9f52-3d6a1b0c7e11"   # mesmo e-mail da persona ficticia do painel
ID_NOVA_APP = "5c0d9e8f-1a2b-4c3d-8e9f-0a1b2c3d4e5f"     # cliente que so existe no app
ID_PARCEIRO_APP = "1d2c3b4a-5e6f-4071-8293-a4b5c6d7e8f9"  # "Drogaria Araujo" (o painel ja tem)
ID_CARTA_APP = "a7c4e2b9-5d31-4f80-9e6b-8c2a1d4f7b55"
ID_CUPOM_APP = "f6b1d803-2e94-4a57-83cd-9b0e5a7c1d22"
CPF_MARCOS_APP = "52998224725"
CPF_NOVA_APP = "39053344705"


def _cliente(id_, nome, email, cpf, instalacao, status="em_ativacao"):
    return (id_, nome, email, cpf, "(31) 98888-1234", "30130-010", "Av. Afonso Pena", "1000", None,
            "Centro", "Belo Horizonte", "MG", "CEMIG", instalacao, status, 1, "2026-05-02T13:20:00Z")


def _criar_banco_app(caminho: Path) -> None:
    with sqlite3.connect(caminho) as con:
        con.executescript(ESQUEMA_APP)
        con.execute("INSERT INTO usinas VALUES (1, 'Usina Solar App', 'Montes Claros, MG', 4200, 'ativa', '2026-03-01')")
        con.execute(
            "INSERT INTO parceiros VALUES (?, 'Drogaria Araújo', 'Farmácia', "
            "'https://cdn.exemplo/araujo.png', 1, '2026-05-20T12:00:00Z', NULL)", (ID_PARCEIRO_APP,))
        con.execute("INSERT INTO dicas VALUES (1, 'Dica exclusiva do app', 'Descricao da dica.', 9.5, '<svg/>', '2026-04-01')")
        con.executemany(
            "INSERT INTO clientes VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [
                _cliente(ID_MARCOS_APP, "Marcos Andrade", "marcos.andrade@email.com", CPF_MARCOS_APP, "3001234567"),
                _cliente(ID_NOVA_APP, "Beatriz Nogueira", "beatriz.nogueira@email.com", CPF_NOVA_APP, "3009998887"),
            ],
        )
        con.executemany(
            "INSERT INTO ativacoes VALUES (?,?,?,?,?,?,?)",
            [
                (ID_MARCOS_APP, 2, "CEMIG", 90, "2026-11-16", "2026-08-18T08:00:00Z", "[]"),
                (ID_NOVA_APP, 1, "CEMIG", 90, "2027-01-30", "2026-11-01T10:00:00Z", '["Conta de luz recebida"]'),
            ],
        )
        con.execute("INSERT INTO ofensivas_clube VALUES (?, 3)", (ID_MARCOS_APP,))
        con.execute("INSERT INTO cartas VALUES (?, ?, 3, 'normal', 'aberta', '2026-06-12T09:00:00Z', "
                    "'2026-06-12T19:42:00Z', ?)", (ID_CARTA_APP, ID_MARCOS_APP, ID_CUPOM_APP))
        con.execute(
            "INSERT INTO cupons VALUES (?, ?, ?, 'PARCERIA', '15% de desconto na Araújo', 'Use na loja.', "
            "'BULBE15', ?, 'Drogaria Araújo', 'Farmácia', 'salvo', '2026-12-15', 30, '2026-06-12T19:42:00Z', NULL)",
            (ID_CUPOM_APP, ID_MARCOS_APP, ID_CARTA_APP, ID_PARCEIRO_APP))
        con.execute("INSERT INTO indicacoes VALUES (1, ?, 'Paula Reis', 'paula@email.com', 'pendente', 50)",
                    (ID_NOVA_APP,))
        con.executemany(
            "INSERT INTO simulacoes VALUES (?,?,?,?,?,?,?,?,?,?)",
            [
                (1, 200, 170, 12, 1, "2026-11-10", ID_NOVA_APP, "verde", 30, 410),
                (2, 350, 297.5, 6, 0, "2026-11-11", None, "amarela", 54.0, 324.0),
            ],
        )
        con.execute(
            "INSERT INTO adesoes VALUES (1, 'João da Silva', 'joao@email.com', '16899535009', '31999999999', "
            "'30575160', 'Rua Oliveira', 213, 'Buritis', 'Belo Horizonte', 'MG', 'CEMIG', '3242412', 399, "
            "'enviada', '2026-06-01')")


def _sha(caminho: Path) -> str:
    return hashlib.sha256(caminho.read_bytes()).hexdigest()


@pytest.fixture(scope="module", autouse=True)
def restaurar_banco_do_painel():
    """Recria o banco do painel no fim do modulo (os testes daqui vinculam/criam clientes)."""
    yield
    sincronizacao.descartar_conexoes()
    sincronizacao.reiniciar_estado()
    api_app.limpar_token()
    conexao.inicializar_banco(recriar=True)


@pytest.fixture
def banco_app(tmp_path, monkeypatch) -> Path:
    caminho = tmp_path / "app.db"
    _criar_banco_app(caminho)
    monkeypatch.setenv("INTEGRACAO_APP_DB_URL", "sqlite:///" + caminho.as_posix())
    yield caminho
    sincronizacao.descartar_conexoes()


def _cliente_painel_por_cpf(cpf: str) -> dict | None:
    encontrados = [c for c in consultas.buscar_clientes(cpf, limite=5) if c["cpf"] == cpf]
    return encontrados[0] if encontrados else None


# ---------------------------------------------------------------------------
# Desligada
# ---------------------------------------------------------------------------
def test_integracao_desligada_nos_testes(cliente_http, cab_admin, cab_atendimento):
    with pytest.raises(sincronizacao.IntegracaoIndisponivel):
        sincronizacao.sincronizar()

    estado = cliente_http.get("/v1/painel/integracao", headers=cab_atendimento)
    assert estado.status_code == 200
    assert estado.json()["ativa"] is False

    resposta = cliente_http.post("/v1/painel/admin/sincronizar", headers=cab_admin)
    assert resposta.status_code == 503
    assert resposta.json()["error"]["code"] == "INTEGRACAO_INDISPONIVEL"
    assert cliente_http.post("/v1/painel/admin/sincronizar", headers=cab_atendimento).status_code == 403
    assert cliente_http.get("/v1/painel/integracao").status_code == 401


def test_banco_do_app_inexistente(monkeypatch, tmp_path):
    monkeypatch.setenv("INTEGRACAO_APP_DB_URL", "sqlite:///" + (tmp_path / "nao-existe.db").as_posix())
    with pytest.raises(sincronizacao.IntegracaoIndisponivel):
        sincronizacao.sincronizar()


# ---------------------------------------------------------------------------
# Sincronizacao app -> painel
# ---------------------------------------------------------------------------
def test_sincronizacao_espelha_o_app_sem_alterar_o_banco_do_app(banco_app, cliente_http, cab_admin):
    antes = _sha(banco_app)
    resposta = cliente_http.post("/v1/painel/admin/sincronizar", headers=cab_admin)
    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    assert corpo["sucesso"] is True
    assert corpo["contagens"]["clientes"]["criados"] == 1
    assert corpo["contagens"]["clientes"]["vinculados"] == 1
    assert corpo["contagens"]["parceiros"]["vinculados"] == 1
    assert _sha(banco_app) == antes, "a sincronizacao nao pode escrever no banco do app"

    # Cliente que so existe no app aparece no painel com o mesmo id e os dados do app.
    nova = cliente_http.get(f"/v1/painel/clientes/{ID_NOVA_APP}", headers=cab_admin)
    assert nova.status_code == 200
    ficha = nova.json()
    assert ficha["cliente"]["origem"] == "app"
    assert ficha["cliente"]["id_app"] == ID_NOVA_APP
    assert ficha["cliente"]["telefone"] == "31988881234"
    assert ficha["ativacao"]["etapa_atual"] == 1
    assert any(e["observacao"] == "Conta de luz recebida" for e in ficha["ativacao"]["eventos"])
    assert [i["nome_indicado"] for i in ficha["indicacoes"]["data"]] == ["Paula Reis"]


def test_persona_do_painel_e_vinculada_e_nao_duplicada(banco_app):
    sincronizacao.sincronizar()
    marcos = [c for c in consultas.buscar_clientes("Marcos Andrade", limite=10) if c["nome"] == "Marcos Andrade"]
    assert len(marcos) == 1
    cliente = consultas.obter_cliente(marcos[0]["id"])
    assert cliente["id_app"] == ID_MARCOS_APP
    assert cliente["cpf"] == CPF_MARCOS_APP
    assert cliente["codigo_indicacao"] == "MARCOS50"  # dado so do painel continua

    # O Clube passa a ser o do app: uma carta aberta e o cupom salvo da Araujo.
    clube = consultas.obter_clube(cliente["id"])
    assert clube["semanas_sequencia"] == 3
    assert [c["id"] for c in clube["cartas_recentes"]] == [ID_CARTA_APP]
    cupons = consultas.listar_cupons(cliente["id"])
    assert [(c["codigo"], c["situacao"]) for c in cupons] == [("BULBE15", "salvo")]

    # Parceiro vinculado pelo nome: continua um so "Drogaria Araujo".
    nomes = [p["nome"] for p in consultas.listar_parceiros(apenas_ativos=False)]
    assert nomes.count("Drogaria Araújo") == 1


def test_sincronizacao_e_idempotente(banco_app):
    sincronizacao.sincronizar()
    segunda = sincronizacao.sincronizar()
    for nome, contagem in segunda["contagens"].items():
        assert contagem["criados"] == 0, nome
        assert contagem["removidos"] == 0, nome
        assert contagem["vinculados"] == 0, nome


def test_simulacoes_e_adesoes_do_app_entram_no_painel(banco_app):
    sincronizacao.sincronizar()
    adesoes = consultas.listar_adesoes_paginado(pagina=1, por_pagina=100)["data"]
    assert any(a["email"] == "joao@email.com" and a["origem"] == "app" for a in adesoes)
    with conexao.obter_sessao() as sessao:
        from sqlalchemy import select

        from app.database.modelos import Simulacao
        simulacoes = sessao.scalars(select(Simulacao).where(Simulacao.importado_do_app.is_(True))).all()
        assert sorted((s.origem, s.economia_total) for s in simulacoes) == [("cliente", 410.0), ("visitante", 324.0)]


def test_mudanca_de_etapa_no_app_vira_evento(banco_app):
    sincronizacao.sincronizar()
    with sqlite3.connect(banco_app) as con:
        con.execute("UPDATE ativacoes SET etapa_atual = 3, atualizado_em = '2026-11-14T10:00:00Z' "
                    "WHERE cliente_id = ?", (ID_NOVA_APP,))
    sincronizacao.sincronizar()
    ativacao = consultas.obter_ativacao(ID_NOVA_APP)
    assert ativacao["etapa_atual"] == 3
    assert any(e["observacao"] == "Etapa 3 registrada no app." for e in ativacao["eventos"])


def test_registro_removido_no_app(banco_app):
    sincronizacao.sincronizar()
    marcos_painel = _cliente_painel_por_cpf(CPF_MARCOS_APP)
    with sqlite3.connect(banco_app) as con:
        con.execute("DELETE FROM indicacoes")
        con.execute("DELETE FROM ativacoes WHERE cliente_id = ?", (ID_NOVA_APP,))
        con.execute("DELETE FROM clientes WHERE id = ?", (ID_NOVA_APP,))
        con.execute("DELETE FROM cupons")
        con.execute("DELETE FROM cartas")
        con.execute("DELETE FROM ofensivas_clube")
        con.execute("DELETE FROM clientes WHERE id = ?", (ID_MARCOS_APP,))
        con.execute("DELETE FROM ativacoes WHERE cliente_id = ?", (ID_MARCOS_APP,))
    resultado = sincronizacao.sincronizar()
    assert resultado["contagens"]["clientes"]["removidos"] == 1
    # Importado: some do painel. Vinculado (persona ficticia): fica, sem vinculo.
    assert consultas.obter_cliente(ID_NOVA_APP) is None
    marcos = consultas.obter_cliente(marcos_painel["id"])
    assert marcos is not None
    assert marcos["id_app"] is None


# ---------------------------------------------------------------------------
# Painel -> app: alterar etapa de ativacao
# ---------------------------------------------------------------------------
class _ApiFalsa(BaseHTTPRequestHandler):
    banco: Path
    requisicoes: list

    def log_message(self, *args):  # silencia o log do http.server
        pass

    def _responder(self, status: int, corpo: dict) -> None:
        bruto = json.dumps(corpo).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(bruto)))
        self.end_headers()
        self.wfile.write(bruto)

    def do_POST(self):  # noqa: N802
        tamanho = int(self.headers.get("Content-Length", 0))
        corpo = self.rfile.read(tamanho).decode()
        self.requisicoes.append(("POST", self.path, corpo))
        if self.path == "/v1/auth/login" and "password=senha-operador" in corpo:
            return self._responder(200, {"access_token": "token-falso", "token_type": "bearer"})
        return self._responder(401, {"error": {"code": "CREDENCIAIS_INVALIDAS", "message": "x", "status": 401}})

    def do_PATCH(self):  # noqa: N802
        tamanho = int(self.headers.get("Content-Length", 0))
        corpo = json.loads(self.rfile.read(tamanho) or b"{}")
        self.requisicoes.append(("PATCH", self.path, corpo))
        if self.headers.get("Authorization") != "Bearer token-falso":
            return self._responder(401, {"error": {"code": "TOKEN_INVALIDO", "message": "x", "status": 401}})
        partes = self.path.strip("/").split("/")  # v1/clientes/{id}/ativacao
        cliente_id = partes[2]
        with sqlite3.connect(self.banco) as con:
            alterados = con.execute(
                "UPDATE ativacoes SET etapa_atual = ?, atualizado_em = '2026-11-15T09:00:00Z' WHERE cliente_id = ?",
                (corpo["etapa_atual"], cliente_id),
            ).rowcount
        if not alterados:
            return self._responder(404, {"error": {"code": "RECURSO_NAO_ENCONTRADO", "message": "Cliente nao encontrado.",
                                                   "status": 404}})
        return self._responder(200, {"cliente_id": cliente_id, "etapa_atual": corpo["etapa_atual"]})


@pytest.fixture
def api_falsa(banco_app, monkeypatch):
    requisicoes: list = []
    manipulador = type("Api", (_ApiFalsa,), {"banco": banco_app, "requisicoes": requisicoes})
    servidor = ThreadingHTTPServer(("127.0.0.1", 0), manipulador)
    thread = threading.Thread(target=servidor.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setenv("INTEGRACAO_APP_API_URL", f"http://127.0.0.1:{servidor.server_address[1]}")
    monkeypatch.setenv("INTEGRACAO_APP_API_EMAIL", "operador@app.local")
    monkeypatch.setenv("INTEGRACAO_APP_API_SENHA", "senha-operador")
    api_app.limpar_token()
    yield requisicoes
    servidor.shutdown()
    servidor.server_close()
    api_app.limpar_token()


def test_painel_altera_etapa_no_app(api_falsa, cliente_http, cab_atendimento, funcionario_atendimento):
    sincronizacao.sincronizar()
    resposta = cliente_http.patch(
        f"/v1/painel/clientes/{ID_NOVA_APP}/ativacao",
        json={"etapa_atual": 4, "observacao": "Documentos conferidos"},
        headers=cab_atendimento,
    )
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["ativacao"]["etapa_atual"] == 4
    assert ("PATCH", f"/v1/clientes/{ID_NOVA_APP}/ativacao",
            {"etapa_atual": 4, "observacao": "Documentos conferidos"}) in api_falsa

    auditoria = consultas.listar_auditoria(funcionario_id=funcionario_atendimento["id"], acao="alterar_ativacao")
    assert auditoria["total"] >= 1
    assert auditoria["data"][0]["recurso_id"] == ID_NOVA_APP


def test_cliente_so_do_painel_nao_pode_ser_alterado(cliente_http, cab_atendimento):
    ficticio = consultas.buscar_clientes(status="em_ativacao", limite=50)
    sem_vinculo = next(c for c in ficticio if consultas.obter_cliente(c["id"])["id_app"] is None)
    resposta = cliente_http.patch(f"/v1/painel/clientes/{sem_vinculo['id']}/ativacao",
                                  json={"etapa_atual": 3}, headers=cab_atendimento)
    assert resposta.status_code == 409
    assert resposta.json()["error"]["code"] == "CLIENTE_SEM_VINCULO_APP"


def test_alterar_etapa_valida_o_corpo_e_o_login(cliente_http, cab_atendimento):
    assert cliente_http.patch(f"/v1/painel/clientes/{ID_NOVA_APP}/ativacao", json={"etapa_atual": 9},
                              headers=cab_atendimento).status_code == 422
    assert cliente_http.patch(f"/v1/painel/clientes/{ID_NOVA_APP}/ativacao",
                              json={"etapa_atual": 2}).status_code == 401


def test_api_do_app_fora_do_ar(banco_app, cliente_http, cab_atendimento, monkeypatch):
    sincronizacao.sincronizar()
    monkeypatch.setenv("INTEGRACAO_APP_API_URL", "http://127.0.0.1:9")
    api_app.limpar_token()
    resposta = cliente_http.patch(f"/v1/painel/clientes/{ID_NOVA_APP}/ativacao", json={"etapa_atual": 2},
                                  headers=cab_atendimento)
    assert resposta.status_code == 503
    assert resposta.json()["error"]["code"] == "APP_INDISPONIVEL"


def test_credenciais_erradas_no_app(api_falsa, cliente_http, cab_atendimento, monkeypatch):
    sincronizacao.sincronizar()
    monkeypatch.setenv("INTEGRACAO_APP_API_SENHA", "errada")
    api_app.limpar_token()
    resposta = cliente_http.patch(f"/v1/painel/clientes/{ID_NOVA_APP}/ativacao", json={"etapa_atual": 2},
                                  headers=cab_atendimento)
    assert resposta.status_code == 502
    assert resposta.json()["error"]["code"] == "APP_CREDENCIAIS_INVALIDAS"
