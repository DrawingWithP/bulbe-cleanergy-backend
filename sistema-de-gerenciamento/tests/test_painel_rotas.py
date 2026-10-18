"""
Rotas do painel (secao 3.2 do contrato de melhorias): paginacao, filtros, rotas novas,
admin x atendimento e auditoria de ver_ficha / ver_auditoria / expurgo.
"""
import math

import pytest

from app.database import consultas

CHAVES_PAGINADO = {"data", "pagina", "por_pagina", "total", "total_paginas"}


def _confere_paginado(corpo: dict, pagina: int, por_pagina: int) -> None:
    assert set(corpo) >= CHAVES_PAGINADO, corpo
    assert corpo["pagina"] == pagina
    assert corpo["por_pagina"] == por_pagina
    assert corpo["total_paginas"] == math.ceil(corpo["total"] / por_pagina)
    assert len(corpo["data"]) <= por_pagina


def _erro_padrao(resposta, status: int) -> dict:
    assert resposta.status_code == status, resposta.text
    erro = resposta.json()["error"]
    assert erro["status"] == status and erro["code"] and erro["message"]
    return erro


@pytest.fixture(scope="module")
def marcos_id() -> str:
    return consultas.buscar_clientes(termo="MARCOS50")[0]["id"]


# ---------------------------------------------------------------------------
# Clientes
# ---------------------------------------------------------------------------
class TestClientes:
    def test_lista_paginada_padrao(self, cliente_http, cab_atendimento):
        resposta = cliente_http.get("/v1/painel/clientes", headers=cab_atendimento)
        assert resposta.status_code == 200
        corpo = resposta.json()
        _confere_paginado(corpo, 1, 20)
        assert corpo["total"] == consultas.buscar_clientes_paginado()["total"]

    def test_paginas(self, cliente_http, cab_atendimento):
        p1 = cliente_http.get("/v1/painel/clientes?pagina=1&por_pagina=10", headers=cab_atendimento).json()
        p2 = cliente_http.get("/v1/painel/clientes?pagina=2&por_pagina=10", headers=cab_atendimento).json()
        _confere_paginado(p1, 1, 10)
        _confere_paginado(p2, 2, 10)
        assert not {c["id"] for c in p1["data"]} & {c["id"] for c in p2["data"]}

    def test_filtros(self, cliente_http, cab_atendimento, marcos_id):
        corpo = cliente_http.get("/v1/painel/clientes?etapa=2&status=em_ativacao&por_pagina=100",
                                 headers=cab_atendimento).json()
        assert corpo["total"] >= 1
        assert all(c["etapa_ativacao"] == 2 and c["status"] == "em_ativacao" for c in corpo["data"])
        assert marcos_id in {c["id"] for c in corpo["data"]}
        por_termo = cliente_http.get("/v1/painel/clientes", params={"termo": "MARCOS50"},
                                     headers=cab_atendimento).json()
        assert [c["id"] for c in por_termo["data"]] == [marcos_id]

    @pytest.mark.parametrize("parametros", ["por_pagina=101", "por_pagina=0", "pagina=0", "etapa=abc"])
    def test_parametros_invalidos(self, cliente_http, cab_atendimento, parametros):
        resposta = cliente_http.get(f"/v1/painel/clientes?{parametros}", headers=cab_atendimento)
        if resposta.status_code == 200:  # implementacao que normaliza em vez de recusar
            corpo = resposta.json()
            assert 1 <= corpo["por_pagina"] <= 100 and corpo["pagina"] >= 1
            assert parametros != "etapa=abc"
        else:
            assert resposta.status_code == 422

    def test_parados_nao_e_capturado_por_id(self, cliente_http, cab_atendimento):
        resposta = cliente_http.get("/v1/painel/clientes/parados", headers=cab_atendimento)
        assert resposta.status_code == 200, resposta.text
        corpo = resposta.json()
        itens = corpo["data"] if isinstance(corpo, dict) else corpo
        assert isinstance(itens, list)
        assert all(i["dias_na_etapa"] >= 30 for i in itens)  # dias_minimos padrao = 30

    def test_parados_com_filtros(self, cliente_http, cab_atendimento):
        resposta = cliente_http.get("/v1/painel/clientes/parados?etapa=2&dias_minimos=0&limite=5",
                                    headers=cab_atendimento)
        assert resposta.status_code == 200
        corpo = resposta.json()
        itens = corpo["data"] if isinstance(corpo, dict) else corpo
        assert 1 <= len(itens) <= 5
        assert all(i["etapa_atual"] == 2 for i in itens)

    def test_ficha_completa(self, cliente_http, cab_atendimento, marcos_id):
        resposta = cliente_http.get(f"/v1/painel/clientes/{marcos_id}", headers=cab_atendimento)
        assert resposta.status_code == 200
        ficha = resposta.json()
        assert set(ficha) >= {"cliente", "ativacao", "faturas", "economia", "indicacoes", "clube", "cupons",
                              "notificacoes", "atendimentos"}
        assert ficha["cliente"]["codigo_indicacao"] == "MARCOS50"
        assert "bonus_clube_total" in ficha["economia"]

    def test_ficha_mostra_bonus_nas_faturas(self, cliente_http, cab_atendimento):
        from sqlalchemy import text

        from app.database.conexao import engine

        with engine.connect() as con:
            cliente_id = con.execute(text("SELECT cliente_id FROM faturas WHERE bonus_clube > 0 LIMIT 1")).scalar()
        ficha = cliente_http.get(f"/v1/painel/clientes/{cliente_id}", headers=cab_atendimento).json()
        assert all("bonus_clube" in f for f in ficha["faturas"])

    def test_ficha_inexistente_404(self, cliente_http, cab_atendimento):
        _erro_padrao(cliente_http.get("/v1/painel/clientes/nao-existe-123", headers=cab_atendimento), 404)

    def test_ficha_grava_ver_ficha(self, cliente_http, criar_funcionario, marcos_id):
        f = criar_funcionario()
        assert cliente_http.get(f"/v1/painel/clientes/{marcos_id}", headers=f["cabecalho"]).status_code == 200
        registros = consultas.listar_auditoria(funcionario_id=f["id"], acao="ver_ficha")
        assert registros["total"] == 1
        item = registros["data"][0]
        assert item["recurso_id"] == marcos_id
        assert item["ip"]

    def test_ficha_inexistente_nao_quebra_auditoria(self, cliente_http, criar_funcionario):
        f = criar_funcionario()
        assert cliente_http.get("/v1/painel/clientes/nao-existe", headers=f["cabecalho"]).status_code == 404


# ---------------------------------------------------------------------------
# Ativacoes, adesoes, atendimentos
# ---------------------------------------------------------------------------
class TestOutrasListas:
    def test_resumo_ativacoes(self, cliente_http, cab_atendimento):
        resposta = cliente_http.get("/v1/painel/ativacoes/resumo", headers=cab_atendimento)
        assert resposta.status_code == 200
        assert resposta.json() == consultas.resumo_ativacoes()

    def test_adesoes_paginadas(self, cliente_http, cab_atendimento):
        corpo = cliente_http.get("/v1/painel/adesoes?situacao=enviada&pagina=1&por_pagina=3",
                                 headers=cab_atendimento).json()
        _confere_paginado(corpo, 1, 3)
        assert all(a["situacao"] == "enviada" for a in corpo["data"])
        assert corpo["total"] == consultas.listar_adesoes_paginado(situacao="enviada")["total"]

    def test_atendimentos_paginados(self, cliente_http, cab_atendimento):
        corpo = cliente_http.get("/v1/painel/atendimentos?status=aberto&pagina=1&por_pagina=4",
                                 headers=cab_atendimento).json()
        _confere_paginado(corpo, 1, 4)
        assert all(a["status"] == "aberto" and a["cliente_nome"] for a in corpo["data"])

    @pytest.mark.parametrize("rota", ["/v1/painel/usinas", "/v1/painel/parceiros", "/v1/painel/dicas"])
    def test_listas_iguais_a_v1(self, cliente_http, cab_atendimento, rota):
        resposta = cliente_http.get(rota, headers=cab_atendimento)
        assert resposta.status_code == 200
        assert isinstance(resposta.json(), list) and resposta.json()

    def test_metricas(self, cliente_http, cab_atendimento):
        corpo = cliente_http.get("/v1/painel/metricas", headers=cab_atendimento).json()
        assert corpo["ativacao_etapa5_descricao"] == "ativados nos últimos 30 dias"
        assert "bonus_pagos" in corpo["clube"]

    def test_interface_estatica(self, cliente_http):
        resposta = cliente_http.get("/painel/")
        assert resposta.status_code == 200
        assert "<html" in resposta.text.lower()


# ---------------------------------------------------------------------------
# Rotas de admin
# ---------------------------------------------------------------------------
class TestAdmin:
    def test_auditoria_admin(self, cliente_http, criar_funcionario):
        admin = criar_funcionario(perfil="admin")
        resposta = cliente_http.get("/v1/painel/auditoria?pagina=1&por_pagina=10", headers=admin["cabecalho"])
        assert resposta.status_code == 200
        corpo = resposta.json()
        _confere_paginado(corpo, 1, 10)
        assert corpo["total"] > 0
        assert all("funcionario_nome" in item and "acao" in item for item in corpo["data"])
        # A propria consulta fica registrada.
        registros = consultas.listar_auditoria(funcionario_id=admin["id"], acao="ver_auditoria")
        assert registros["total"] == 1

    def test_auditoria_filtros(self, cliente_http, criar_funcionario):
        admin = criar_funcionario(perfil="admin")
        alvo = criar_funcionario()
        consultas.registrar_auditoria("ver_ficha", funcionario_id=alvo["id"], recurso_id="x")
        corpo = cliente_http.get(f"/v1/painel/auditoria?funcionario_id={alvo['id']}&acao=ver_ficha",
                                 headers=admin["cabecalho"]).json()
        assert corpo["total"] == 1
        assert corpo["data"][0]["funcionario_id"] == alvo["id"]

    def test_auditoria_atendimento_403_sem_registrar(self, cliente_http, criar_funcionario):
        f = criar_funcionario()
        _erro_padrao(cliente_http.get("/v1/painel/auditoria", headers=f["cabecalho"]), 403)
        assert consultas.listar_auditoria(funcionario_id=f["id"], acao="ver_auditoria")["total"] == 0

    def test_uso_chatbot(self, cliente_http, cab_admin, cab_atendimento):
        _erro_padrao(cliente_http.get("/v1/painel/uso-chatbot", headers=cab_atendimento), 403)
        resposta = cliente_http.get("/v1/painel/uso-chatbot?dias=7", headers=cab_admin)
        assert resposta.status_code == 200
        corpo = resposta.json()
        assert corpo["periodo_dias"] == 7
        assert set(corpo) >= {"perguntas", "custo_estimado_usd", "por_funcionario", "ferramentas_mais_usadas",
                              "por_dia"}

    def test_expurgo(self, cliente_http, criar_funcionario, cab_atendimento):
        _erro_padrao(cliente_http.post("/v1/painel/admin/expurgo", headers=cab_atendimento), 403)
        admin = criar_funcionario(perfil="admin")
        resposta = cliente_http.post("/v1/painel/admin/expurgo", headers=admin["cabecalho"])
        assert resposta.status_code == 200, resposta.text
        corpo = resposta.json()
        contagens = corpo if "auditoria" in corpo else next(
            (v for v in corpo.values() if isinstance(v, dict) and "auditoria" in v), {})
        assert set(contagens) >= {"chat_historico", "chat_conversas", "chat_mensagens", "auditoria"}
        assert consultas.listar_auditoria(funcionario_id=admin["id"], acao="expurgo")["total"] == 1
