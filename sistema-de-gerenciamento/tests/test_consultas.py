"""
Consultas de app.database.consultas (secao 1.2 do contrato de melhorias):
formatos, filtros, paginacao, clientes parados, resumo de ativacoes, metricas e bonus do Clube.
"""
import json
import math

import pytest
from sqlalchemy import text

from app.database import consultas
from app.database.conexao import engine

CHAVES_PAGINADO = {"data", "pagina", "por_pagina", "total", "total_paginas"}
CHAVES_CLIENTE_BUSCA = {"id", "nome", "email", "cpf", "telefone", "cidade", "uf", "status", "etapa_ativacao", "criado_em"}
CHAVES_PARADO = {"cliente_id", "nome", "cidade", "etapa_atual", "nome_etapa", "dias_na_etapa",
                 "dias_desde_cadastro", "previsao_conclusao", "atrasado"}


def _sql(consulta: str, **parametros):
    with engine.connect() as con:
        return con.execute(text(consulta), parametros).mappings().all()


def _escalar(consulta: str, **parametros):
    with engine.connect() as con:
        return con.execute(text(consulta), parametros).scalar()


def _json_serializavel(valor) -> None:
    json.dumps(valor)  # levanta TypeError se houver objeto ORM, date etc.


def _confere_paginado(resultado: dict, pagina: int, por_pagina: int) -> None:
    assert set(resultado) >= CHAVES_PAGINADO, resultado.keys()
    assert resultado["pagina"] == pagina
    assert resultado["por_pagina"] == por_pagina
    assert isinstance(resultado["total"], int) and resultado["total"] >= 0
    assert resultado["total_paginas"] == math.ceil(resultado["total"] / por_pagina)
    assert isinstance(resultado["data"], list)
    assert len(resultado["data"]) <= por_pagina
    _json_serializavel(resultado)


@pytest.fixture(scope="module")
def marcos() -> dict:
    encontrados = consultas.buscar_clientes(termo="MARCOS50")
    assert encontrados, "Persona Marcos Andrade (MARCOS50) nao encontrada no seed."
    return encontrados[0]


# ---------------------------------------------------------------------------
# buscar_clientes e buscar_clientes_paginado
# ---------------------------------------------------------------------------
class TestBuscarClientes:
    def test_formato_e_compatibilidade_v1(self, marcos):
        assert set(marcos) >= CHAVES_CLIENTE_BUSCA
        assert marcos["nome"] == "Marcos Andrade"
        assert marcos["status"] == "em_ativacao"
        assert marcos["etapa_ativacao"] == 2

    def test_filtro_por_etapa(self, marcos):
        resultado = consultas.buscar_clientes(etapa=2, limite=100)
        assert resultado
        assert all(c["etapa_ativacao"] == 2 for c in resultado)
        assert marcos["id"] in {c["id"] for c in resultado}
        assert consultas.buscar_clientes(etapa=3, termo="MARCOS50") == []

    def test_paginado_formato(self):
        resultado = consultas.buscar_clientes_paginado(pagina=1, por_pagina=7)
        _confere_paginado(resultado, 1, 7)
        assert resultado["total"] == _escalar("SELECT COUNT(*) FROM clientes")
        assert len(resultado["data"]) == 7
        assert set(resultado["data"][0]) >= CHAVES_CLIENTE_BUSCA

    def test_paginas_cobrem_todos_sem_repetir(self):
        primeira = consultas.buscar_clientes_paginado(por_pagina=9)
        ids: list[str] = []
        for pagina in range(1, primeira["total_paginas"] + 1):
            resultado = consultas.buscar_clientes_paginado(pagina=pagina, por_pagina=9)
            _confere_paginado(resultado, pagina, 9)
            ids.extend(c["id"] for c in resultado["data"])
        assert len(ids) == len(set(ids)) == primeira["total"]

    def test_pagina_alem_da_ultima_vem_vazia(self):
        resultado = consultas.buscar_clientes_paginado(pagina=9999, por_pagina=20)
        assert resultado["data"] == []
        assert resultado["total"] > 0

    def test_por_pagina_limitado_a_100(self):
        resultado = consultas.buscar_clientes_paginado(por_pagina=1000)
        assert 1 <= resultado["por_pagina"] <= 100
        assert len(resultado["data"]) <= 100

    def test_por_pagina_minimo_1(self):
        resultado = consultas.buscar_clientes_paginado(por_pagina=0)
        assert resultado["por_pagina"] >= 1

    def test_filtros_status_cidade_termo_etapa(self, marcos):
        ativos = consultas.buscar_clientes_paginado(status="ativo", por_pagina=100)
        assert ativos["total"] == _escalar("SELECT COUNT(*) FROM clientes WHERE status = 'ativo'")
        assert all(c["status"] == "ativo" for c in ativos["data"])

        por_termo = consultas.buscar_clientes_paginado(termo="Marcos Andrade")
        assert marcos["id"] in {c["id"] for c in por_termo["data"]}

        por_cidade = consultas.buscar_clientes_paginado(cidade=marcos["cidade"], por_pagina=100)
        assert por_cidade["total"] >= 1
        assert all(marcos["cidade"].lower() in c["cidade"].lower() for c in por_cidade["data"])

        etapa2 = consultas.buscar_clientes_paginado(etapa=2, por_pagina=100)
        assert etapa2["total"] >= 1
        assert all(c["etapa_ativacao"] == 2 for c in etapa2["data"])

    def test_status_invalido_devolve_vazio(self):
        resultado = consultas.buscar_clientes_paginado(status="inexistente")
        assert resultado["total"] == 0
        assert resultado["data"] == []


# ---------------------------------------------------------------------------
# Clientes parados e resumo de ativacoes
# ---------------------------------------------------------------------------
class TestAtivacoes:
    def test_parados_formato_e_ordem(self):
        resultado = consultas.listar_clientes_parados(dias_minimos=0, limite=100)
        _json_serializavel(resultado)
        assert isinstance(resultado, list) and resultado
        for item in resultado:
            assert set(item) >= CHAVES_PARADO
            assert isinstance(item["atrasado"], bool)
            assert 1 <= item["etapa_atual"] <= 5
            assert item["dias_na_etapa"] >= 0
        dias = [item["dias_na_etapa"] for item in resultado]
        assert dias == sorted(dias, reverse=True), "Deve vir do mais parado ao menos parado."

    def test_parados_sao_clientes_em_ativacao(self):
        resultado = consultas.listar_clientes_parados(dias_minimos=0, limite=100)
        em_ativacao = {r["id"] for r in _sql("SELECT id FROM clientes WHERE status = 'em_ativacao'")}
        assert {item["cliente_id"] for item in resultado} == em_ativacao

    def test_parados_respeita_dias_minimos(self):
        for dias_minimos in (10, 30, 60):
            resultado = consultas.listar_clientes_parados(dias_minimos=dias_minimos, limite=100)
            assert all(item["dias_na_etapa"] >= dias_minimos for item in resultado)

    def test_parados_filtro_etapa_e_limite(self):
        etapa2 = consultas.listar_clientes_parados(etapa=2, dias_minimos=0, limite=100)
        assert etapa2 and all(item["etapa_atual"] == 2 for item in etapa2)
        assert len(consultas.listar_clientes_parados(dias_minimos=0, limite=3)) <= 3

    def test_parados_atrasado_segue_90_dias_do_cadastro(self):
        for item in consultas.listar_clientes_parados(dias_minimos=0, limite=100):
            if item["dias_desde_cadastro"] > 90:
                assert item["atrasado"] is True, item
            elif item["dias_desde_cadastro"] < 90:
                assert item["atrasado"] is False, item

    def test_resumo_ativacoes_formato(self):
        resumo = consultas.resumo_ativacoes()
        _json_serializavel(resumo)
        assert set(resumo) >= {"em_ativacao", "por_etapa", "dias_medios_na_etapa", "atrasados_90_dias",
                               "ativados_30_dias", "tempo_medio_ativacao_dias"}
        assert set(resumo["por_etapa"]) == {"1", "2", "3", "4"}
        assert set(resumo["dias_medios_na_etapa"]) == {"1", "2", "3", "4"}
        assert all(isinstance(v, (int, float)) and v >= 0 for v in resumo["dias_medios_na_etapa"].values())
        assert resumo["tempo_medio_ativacao_dias"] is None or resumo["tempo_medio_ativacao_dias"] >= 0

    def test_resumo_ativacoes_coerente(self):
        resumo = consultas.resumo_ativacoes()
        em_ativacao = _escalar("SELECT COUNT(*) FROM clientes WHERE status = 'em_ativacao'")
        assert resumo["em_ativacao"] == em_ativacao
        assert sum(resumo["por_etapa"].values()) <= em_ativacao
        parados = consultas.listar_clientes_parados(dias_minimos=0, limite=100)
        assert resumo["atrasados_90_dias"] == sum(1 for p in parados if p["atrasado"])
        assert 0 <= resumo["ativados_30_dias"] <= _escalar("SELECT COUNT(*) FROM clientes WHERE status = 'ativo'")


# ---------------------------------------------------------------------------
# Metricas gerais
# ---------------------------------------------------------------------------
class TestMetricas:
    def test_metricas_v2(self):
        metricas = consultas.metricas_gerais()
        _json_serializavel(metricas)
        assert metricas["ativacao_etapa5_descricao"] == "ativados nos últimos 30 dias"
        assert set(metricas["ativacao_por_etapa"]) == {"1", "2", "3", "4", "5"}
        assert metricas["ativacao_por_etapa"]["5"] == consultas.resumo_ativacoes()["ativados_30_dias"]
        for chave in ("clientes", "faturas", "economia_total_gerada", "indicacoes", "clube", "adesoes",
                      "simulacoes_30_dias", "app"):
            assert chave in metricas

    def test_bonus_pagos_soma_bonus_clube(self):
        metricas = consultas.metricas_gerais()
        soma = _escalar("SELECT COALESCE(SUM(bonus_clube), 0) FROM faturas")
        assert metricas["clube"]["bonus_pagos"] == pytest.approx(soma, abs=0.01)


# ---------------------------------------------------------------------------
# Bonus do Clube nas faturas
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def cliente_com_bonus() -> str:
    linha = _sql("SELECT cliente_id FROM faturas WHERE bonus_clube > 0 LIMIT 1")
    assert linha
    return linha[0]["cliente_id"]


class TestBonusClube:
    def test_seed_aplica_bonus_de_50(self):
        linhas = _sql("SELECT bonus_clube FROM faturas WHERE bonus_clube > 0")
        assert linhas, "O seed deve aplicar o bonus do Clube em ao menos uma fatura."
        assert all(float(l["bonus_clube"]) <= 50.0 + 1e-9 for l in linhas)
        assert any(float(l["bonus_clube"]) == pytest.approx(50.0) for l in linhas)

    def test_valor_total_desconta_bonus_sem_ficar_negativo(self):
        linhas = _sql("SELECT valor_sem_bulbe, desconto, bonus_indicacao, bonus_clube, valor_total FROM faturas")
        for l in linhas:
            assert l["valor_total"] >= 0
            esperado = max(0.0, l["valor_sem_bulbe"] - l["desconto"] - l["bonus_indicacao"] - l["bonus_clube"])
            assert l["valor_total"] == pytest.approx(esperado, abs=0.011), dict(l)

    def test_listar_faturas_traz_bonus_clube(self, cliente_com_bonus):
        faturas = consultas.listar_faturas(cliente_com_bonus, limite=120)
        assert faturas and all("bonus_clube" in f for f in faturas)
        assert any(f["bonus_clube"] > 0 for f in faturas)

    def test_listar_faturas_vencidas_traz_bonus_clube(self):
        vencidas = consultas.listar_faturas_vencidas(limite=100)
        assert vencidas
        assert all("bonus_clube" in f for f in vencidas)

    def test_resumo_economia_soma_bonus_clube(self, cliente_com_bonus):
        resumo = consultas.resumo_economia_cliente(cliente_com_bonus)
        assert "bonus_clube_total" in resumo
        soma = _escalar("SELECT SUM(bonus_clube) FROM faturas WHERE cliente_id = :c", c=cliente_com_bonus)
        assert resumo["bonus_clube_total"] == pytest.approx(soma, abs=0.01)
        assert resumo["economia_total"] == pytest.approx(
            resumo["economia_total_desconto"] + resumo["bonus_indicacao_total"] + resumo["bonus_clube_total"],
            abs=0.011,
        )


# ---------------------------------------------------------------------------
# Adesoes e atendimentos paginados
# ---------------------------------------------------------------------------
class TestPaginadasAdesoesAtendimentos:
    def test_adesoes_paginado(self):
        resultado = consultas.listar_adesoes_paginado(pagina=1, por_pagina=5)
        _confere_paginado(resultado, 1, 5)
        assert resultado["total"] == _escalar("SELECT COUNT(*) FROM adesoes")

    def test_adesoes_filtro_situacao_soma_total(self):
        total = consultas.listar_adesoes_paginado(por_pagina=100)["total"]
        soma = 0
        for situacao in ("rascunho", "enviada", "aprovada", "recusada"):
            parcial = consultas.listar_adesoes_paginado(situacao=situacao, por_pagina=100)
            assert all(a["situacao"] == situacao for a in parcial["data"])
            soma += parcial["total"]
        assert soma == total
        assert consultas.listar_adesoes_paginado(situacao="invalida")["total"] == 0

    def test_clara_ribeiro_com_adesao_enviada(self):
        enviadas = consultas.listar_adesoes_paginado(situacao="enviada", por_pagina=100)["data"]
        assert "Clara Ribeiro" in {a["nome"] for a in enviadas}

    def test_atendimentos_paginado(self):
        resultado = consultas.listar_atendimentos_paginado(pagina=2, por_pagina=4)
        _confere_paginado(resultado, 2, 4)
        assert resultado["total"] == _escalar("SELECT COUNT(*) FROM atendimentos")
        assert all("cliente_nome" in a and a["cliente_nome"] for a in resultado["data"])

    def test_atendimentos_filtros(self):
        abertos = consultas.listar_atendimentos_paginado(status="aberto", por_pagina=100)
        assert abertos["total"] == _escalar("SELECT COUNT(*) FROM atendimentos WHERE status = 'aberto'")
        assert all(a["status"] == "aberto" for a in abertos["data"])
        cliente_id = _sql("SELECT cliente_id FROM atendimentos LIMIT 1")[0]["cliente_id"]
        do_cliente = consultas.listar_atendimentos_paginado(cliente_id=cliente_id, por_pagina=100)
        assert do_cliente["total"] >= 1
        assert all(a["cliente_id"] == cliente_id for a in do_cliente["data"])


# ---------------------------------------------------------------------------
# Estado inicial do seed (v2)
# ---------------------------------------------------------------------------
class TestSeedV2:
    def test_chat_comeca_vazio(self, banco_de_teste):
        assert banco_de_teste["chat_conversas"] == 0
        assert banco_de_teste["chat_mensagens"] == 0

    def test_auditoria_plausivel(self, banco_de_teste):
        quantidade = banco_de_teste["auditoria_acessos"]
        assert quantidade is not None and 60 <= quantidade <= 300, quantidade
        permitidas = {"login_ok", "login_falha", "login_bloqueado", "alerta_email", "ver_ficha",
                      "ver_auditoria", "expurgo"}
        assert set(banco_de_teste["acoes_auditoria"]) <= permitidas
