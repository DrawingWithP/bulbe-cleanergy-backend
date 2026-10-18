"""
Consultas de conversas do chat (so de acrescimo), registro de uso/custo, auditoria de acessos,
contagem de falhas de login e expurgo por retencao (secao 1.2 do contrato de melhorias).
"""
import json
import time
import uuid
from datetime import timedelta

import pytest
from sqlalchemy import select, text, update

from app.database import consultas
from app.database.conexao import Base, engine
from tests.apoio import agora_utc, dias_atras

CHAVES_CONVERSA = {"id", "titulo", "criado_em", "atualizado_em"}


def _tabela(nome: str):
    from app.database import modelos  # noqa: F401  (registra as tabelas)

    return Base.metadata.tables[nome]


def _linhas(consulta: str, **parametros) -> list[dict]:
    with engine.connect() as con:
        return [dict(l) for l in con.execute(text(consulta), parametros).mappings().all()]


def _atualizar(tabela: str, valores: dict, **filtros) -> None:
    t = _tabela(tabela)
    condicao = [t.c[coluna] == valor for coluna, valor in filtros.items()]
    with engine.begin() as con:
        con.execute(update(t).where(*condicao).values(**valores))


def _uuid_valido(valor: str) -> bool:
    try:
        uuid.UUID(str(valor))
        return True
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# Conversas
# ---------------------------------------------------------------------------
class TestConversas:
    def test_criar_conversa(self, criar_funcionario):
        f = criar_funcionario()
        conversa = consultas.criar_conversa(f["id"], "Clientes parados na etapa 2")
        assert set(conversa) >= CHAVES_CONVERSA
        assert _uuid_valido(conversa["id"])
        assert conversa["titulo"] == "Clientes parados na etapa 2"
        json.dumps(conversa)

    def test_titulo_limitado_a_120(self, criar_funcionario):
        f = criar_funcionario()
        conversa = consultas.criar_conversa(f["id"], "x" * 300)
        assert len(conversa["titulo"]) <= 120
        salvo = consultas.obter_conversa(conversa["id"], f["id"])
        assert len(salvo["titulo"]) <= 120

    def test_listar_conversas_mais_recentes_primeiro(self, criar_funcionario):
        f = criar_funcionario()
        primeira = consultas.criar_conversa(f["id"], "Primeira")
        time.sleep(1.1)
        segunda = consultas.criar_conversa(f["id"], "Segunda")
        consultas.adicionar_mensagens(segunda["id"], [
            {"papel": "user", "conteudo": "oi", "texto": "oi"},
            {"papel": "assistant", "conteudo": [{"type": "text", "text": "olá"}], "texto": "olá"},
        ])
        lista = consultas.listar_conversas(f["id"])
        assert [c["id"] for c in lista] == [segunda["id"], primeira["id"]]
        totais = {c["id"]: c["total_mensagens"] for c in lista}
        assert totais == {segunda["id"]: 2, primeira["id"]: 0}
        assert all(set(c) >= CHAVES_CONVERSA | {"total_mensagens"} for c in lista)
        assert len(consultas.listar_conversas(f["id"], limite=1)) == 1

    def test_listar_conversas_so_do_funcionario(self, criar_funcionario):
        f1, f2 = criar_funcionario(), criar_funcionario()
        conversa = consultas.criar_conversa(f1["id"], "Só minha")
        assert conversa["id"] not in {c["id"] for c in consultas.listar_conversas(f2["id"])}

    def test_obter_conversa_de_outro_funcionario_ou_inexistente(self, criar_funcionario):
        f1, f2 = criar_funcionario(), criar_funcionario()
        conversa = consultas.criar_conversa(f1["id"], "Privada")
        assert consultas.obter_conversa(conversa["id"], f2["id"]) is None
        assert consultas.obter_conversa(str(uuid.uuid4()), f1["id"]) is None
        assert consultas.obter_conversa(conversa["id"], f1["id"]) is not None

    def test_mensagens_guardam_conteudo_exato(self, criar_funcionario):
        f = criar_funcionario()
        conversa = consultas.criar_conversa(f["id"], "Conteúdo exato")
        bloco_assistente = [
            {"type": "thinking", "thinking": "Preciso buscar o cliente João.", "signature": "c2lnbmF0dXJh=="},
            {"type": "text", "text": "Vou consultar."},
            {"type": "tool_use", "id": "toolu_01", "name": "buscar_clientes",
             "input": {"termo": "João", "etapa": 2, "limite": 5}},
        ]
        resultado_ferramenta = [
            {"type": "tool_result", "tool_use_id": "toolu_01", "content": "[{\"nome\": \"João\"}]",
             "is_error": False},
        ]
        mensagens = [
            {"papel": "user", "conteudo": "[Contexto: hoje é 18/10/2026] Quem é o João?", "texto": "Quem é o João?"},
            {"papel": "assistant", "conteudo": bloco_assistente, "texto": "Vou consultar."},
            {"papel": "user", "conteudo": resultado_ferramenta, "texto": ""},
        ]
        consultas.adicionar_mensagens(conversa["id"], mensagens)
        salvo = consultas.obter_conversa(conversa["id"], f["id"])
        json.dumps(salvo)
        assert set(salvo) >= CHAVES_CONVERSA | {"mensagens"}
        assert [m["papel"] for m in salvo["mensagens"]] == ["user", "assistant", "user"]
        assert [m["conteudo"] for m in salvo["mensagens"]] == [m["conteudo"] for m in mensagens]
        assert [m["texto"] for m in salvo["mensagens"]] == [m["texto"] for m in mensagens]
        ordens = [m["ordem"] for m in salvo["mensagens"]]
        assert ordens == sorted(ordens) and len(set(ordens)) == len(ordens)
        # O JSON gravado no banco e o conteudo exato.
        brutos = _linhas("SELECT conteudo_json FROM chat_mensagens WHERE conversa_id = :c ORDER BY ordem",
                         c=conversa["id"])
        assert [json.loads(l["conteudo_json"]) for l in brutos] == [m["conteudo"] for m in mensagens]

    def test_historico_so_de_acrescimo(self, criar_funcionario):
        f = criar_funcionario()
        conversa = consultas.criar_conversa(f["id"], "Acréscimo")
        consultas.adicionar_mensagens(conversa["id"], [
            {"papel": "user", "conteudo": "pergunta 1", "texto": "pergunta 1"},
            {"papel": "assistant", "conteudo": [{"type": "text", "text": "resposta 1"}], "texto": "resposta 1"},
        ])
        antes = consultas.obter_conversa(conversa["id"], f["id"])
        brutos_antes = _linhas("SELECT * FROM chat_mensagens WHERE conversa_id = :c ORDER BY ordem",
                               c=conversa["id"])
        time.sleep(1.1)
        consultas.adicionar_mensagens(conversa["id"], [
            {"papel": "user", "conteudo": "pergunta 2", "texto": "pergunta 2"},
            {"papel": "assistant", "conteudo": [{"type": "text", "text": "resposta 2"}], "texto": "resposta 2"},
        ])
        depois = consultas.obter_conversa(conversa["id"], f["id"])
        brutos_depois = _linhas("SELECT * FROM chat_mensagens WHERE conversa_id = :c ORDER BY ordem",
                                c=conversa["id"])
        assert len(depois["mensagens"]) == 4
        assert depois["mensagens"][:2] == antes["mensagens"]
        assert brutos_depois[:2] == brutos_antes, "Mensagens antigas nao podem ser alteradas."
        assert [m["texto"] for m in depois["mensagens"]] == ["pergunta 1", "resposta 1", "pergunta 2", "resposta 2"]
        assert min(m["ordem"] for m in depois["mensagens"][2:]) > max(m["ordem"] for m in antes["mensagens"])
        assert depois["atualizado_em"] > antes["atualizado_em"]

    def test_ordem_unica_por_conversa(self, criar_funcionario):
        f = criar_funcionario()
        c1 = consultas.criar_conversa(f["id"], "C1")
        c2 = consultas.criar_conversa(f["id"], "C2")
        for c in (c1, c2):
            consultas.adicionar_mensagens(c["id"], [{"papel": "user", "conteudo": "a", "texto": "a"}])
            consultas.adicionar_mensagens(c["id"], [{"papel": "assistant", "conteudo": "b", "texto": "b"}])
        for c in (c1, c2):
            ordens = [m["ordem"] for m in consultas.obter_conversa(c["id"], f["id"])["mensagens"]]
            assert len(ordens) == 2 and ordens[0] < ordens[1]


# ---------------------------------------------------------------------------
# registrar_chat (uso/custo) e metricas_uso_chatbot
# ---------------------------------------------------------------------------
class TestUsoChatbot:
    def test_registrar_chat_compativel_com_v1(self, criar_funcionario):
        f = criar_funcionario()
        consultas.registrar_chat(f["id"], "pergunta v1", "resposta v1", ["listar_dicas"])
        linha = _linhas("SELECT * FROM chat_historico WHERE funcionario_id = :f ORDER BY id", f=f["id"])[-1]
        assert linha["pergunta"] == "pergunta v1"
        assert json.loads(linha["ferramentas_usadas"]) == ["listar_dicas"]
        assert linha["conversa_id"] is None
        assert (linha["input_tokens"] or 0) == 0
        assert (linha["custo_estimado_usd"] or 0) == 0

    def test_registrar_chat_com_uso(self, criar_funcionario):
        f = criar_funcionario()
        conversa = consultas.criar_conversa(f["id"], "Com uso")
        uso = {"input_tokens": 1200, "output_tokens": 340, "cache_read_tokens": 5000,
               "cache_creation_tokens": 800, "custo_estimado_usd": 0.000495}
        consultas.registrar_chat(f["id"], "p", "r", ["buscar_clientes"], conversa_id=conversa["id"],
                                 modelo="claude-haiku-5-5", uso=uso, duracao_ms=1234)
        linha = _linhas("SELECT * FROM chat_historico WHERE funcionario_id = :f ORDER BY id", f=f["id"])[-1]
        assert linha["conversa_id"] == conversa["id"]
        assert linha["modelo"] == "claude-haiku-5-5"
        assert linha["input_tokens"] == 1200
        assert linha["output_tokens"] == 340
        assert linha["cache_read_tokens"] == 5000
        assert linha["cache_creation_tokens"] == 800
        assert linha["custo_estimado_usd"] == pytest.approx(0.000495)
        assert linha["duracao_ms"] == 1234

    def test_metricas_uso_chatbot(self, criar_funcionario):
        f = criar_funcionario()
        antes = consultas.metricas_uso_chatbot(dias=30)
        chaves = {"periodo_dias", "perguntas", "conversas", "funcionarios_ativos", "input_tokens",
                  "output_tokens", "cache_read_tokens", "custo_estimado_usd", "custo_medio_por_pergunta_usd",
                  "duracao_media_ms", "por_funcionario", "ferramentas_mais_usadas", "por_dia"}
        assert set(antes) >= chaves
        assert antes["periodo_dias"] == 30
        conversa = consultas.criar_conversa(f["id"], "Métricas")
        for i in range(2):
            consultas.registrar_chat(
                f["id"], f"p{i}", f"r{i}", ["resumo_ativacoes", "listar_clientes_parados"],
                conversa_id=conversa["id"], modelo="claude-haiku-5-5",
                uso={"input_tokens": 1000, "output_tokens": 100, "cache_read_tokens": 0,
                     "cache_creation_tokens": 0, "custo_estimado_usd": 0.25},
                duracao_ms=500,
            )
        depois = consultas.metricas_uso_chatbot(dias=30)
        json.dumps(depois)
        assert depois["perguntas"] == antes["perguntas"] + 2
        assert depois["input_tokens"] == antes["input_tokens"] + 2000
        assert depois["output_tokens"] == antes["output_tokens"] + 200
        assert depois["custo_estimado_usd"] == pytest.approx(antes["custo_estimado_usd"] + 0.5, abs=1e-6)
        assert depois["custo_medio_por_pergunta_usd"] == pytest.approx(
            depois["custo_estimado_usd"] / depois["perguntas"], rel=1e-3, abs=1e-6)
        meu = [p for p in depois["por_funcionario"] if p["funcionario_id"] == f["id"]]
        assert meu and meu[0]["perguntas"] == 2 and meu[0]["custo_estimado_usd"] == pytest.approx(0.5)
        assert meu[0]["nome"] == f["nome"]
        nomes = {item["nome"]: item["usos"] for item in depois["ferramentas_mais_usadas"]}
        assert nomes.get("resumo_ativacoes", 0) >= 2
        usos = [item["usos"] for item in depois["ferramentas_mais_usadas"]]
        assert usos == sorted(usos, reverse=True)
        assert depois["por_dia"] and all(set(d) >= {"data", "perguntas", "custo_estimado_usd"} for d in depois["por_dia"])
        assert sum(d["perguntas"] for d in depois["por_dia"]) == depois["perguntas"]


# ---------------------------------------------------------------------------
# Auditoria
# ---------------------------------------------------------------------------
class TestAuditoria:
    def test_registrar_e_listar(self, criar_funcionario):
        f = criar_funcionario()
        consultas.registrar_auditoria("ver_ficha", funcionario_id=f["id"], recurso_tipo="cliente",
                                      recurso_id="cliente-xyz", ip="10.0.0.1", detalhe="teste")
        resultado = consultas.listar_auditoria(funcionario_id=f["id"])
        assert set(resultado) >= {"data", "pagina", "por_pagina", "total", "total_paginas"}
        assert resultado["por_pagina"] == 50 and resultado["pagina"] == 1
        assert resultado["total"] == 1
        item = resultado["data"][0]
        assert item["acao"] == "ver_ficha"
        assert item["funcionario_id"] == f["id"]
        assert item["funcionario_nome"] == f["nome"]
        assert item["recurso_tipo"] == "cliente" and item["recurso_id"] == "cliente-xyz"
        assert item["ip"] == "10.0.0.1"
        json.dumps(resultado)

    def test_filtro_por_acao_e_paginacao(self, criar_funcionario):
        f = criar_funcionario()
        for _ in range(3):
            consultas.registrar_auditoria("login_ok", funcionario_id=f["id"], ip="10.0.0.2")
        consultas.registrar_auditoria("ver_auditoria", funcionario_id=f["id"])
        so_login = consultas.listar_auditoria(funcionario_id=f["id"], acao="login_ok", por_pagina=2)
        assert so_login["total"] == 3 and so_login["total_paginas"] == 2
        assert len(so_login["data"]) == 2
        assert all(i["acao"] == "login_ok" for i in so_login["data"])
        pagina2 = consultas.listar_auditoria(funcionario_id=f["id"], acao="login_ok", pagina=2, por_pagina=2)
        assert len(pagina2["data"]) == 1

    def test_login_falha_de_email_inexistente(self):
        email = f"ninguem.{uuid.uuid4().hex[:8]}@exemplo.com"
        consultas.registrar_auditoria("login_falha", email_informado=email, ip="10.0.0.3")
        itens = consultas.listar_auditoria(acao="login_falha", por_pagina=100)["data"]
        meu = [i for i in itens if i.get("email_informado") == email]
        assert meu and meu[0]["funcionario_id"] is None

    def test_detalhe_limitado_a_500(self, criar_funcionario):
        f = criar_funcionario()
        consultas.registrar_auditoria("expurgo", funcionario_id=f["id"], detalhe="d" * 2000)
        item = consultas.listar_auditoria(funcionario_id=f["id"])["data"][0]
        assert len(item["detalhe"]) <= 500

    def test_contar_falhas_login_case_insensitive(self):
        email = f"Falhas.{uuid.uuid4().hex[:8]}@Exemplo.com"
        assert consultas.contar_falhas_login(email) == 0
        consultas.registrar_auditoria("login_falha", email_informado=email)
        consultas.registrar_auditoria("login_falha", email_informado=email.lower())
        consultas.registrar_auditoria("login_falha", email_informado=email.upper())
        consultas.registrar_auditoria("login_ok", email_informado=email)  # nao conta
        assert consultas.contar_falhas_login(email.lower()) == 3
        assert consultas.contar_falhas_login(email.upper()) == 3

    def test_contar_falhas_respeita_janela(self):
        email = f"janela.{uuid.uuid4().hex[:8]}@exemplo.com"
        consultas.registrar_auditoria("login_falha", email_informado=email)
        consultas.registrar_auditoria("login_falha", email_informado=email)
        assert consultas.contar_falhas_login(email, minutos=15) == 2
        # Envelhece uma das falhas para 20 minutos atras.
        t = _tabela("auditoria_acessos")
        with engine.begin() as con:
            primeiro_id = con.execute(
                select(t.c.id).where(t.c.email_informado == email).order_by(t.c.id).limit(1)
            ).scalar_one()
            con.execute(update(t).where(t.c.id == primeiro_id)
                        .values(criado_em=agora_utc() - timedelta(minutes=20)))
        assert consultas.contar_falhas_login(email, minutos=15) == 1
        assert consultas.contar_falhas_login(email, minutos=30) == 2


# ---------------------------------------------------------------------------
# Expurgo (retencao)
# ---------------------------------------------------------------------------
class TestExpurgo:
    def test_expurgo_apaga_so_o_antigo(self, criar_funcionario):
        f = criar_funcionario()
        # Conversa antiga (200 dias) com mensagens e historico; conversa recente.
        antiga = consultas.criar_conversa(f["id"], "Antiga")
        consultas.adicionar_mensagens(antiga["id"], [
            {"papel": "user", "conteudo": "velha", "texto": "velha"},
            {"papel": "assistant", "conteudo": [{"type": "text", "text": "velha"}], "texto": "velha"},
        ])
        recente = consultas.criar_conversa(f["id"], "Recente")
        consultas.adicionar_mensagens(recente["id"], [{"papel": "user", "conteudo": "nova", "texto": "nova"}])
        consultas.registrar_chat(f["id"], "pergunta antiga", "r", [], conversa_id=antiga["id"])
        consultas.registrar_chat(f["id"], "pergunta recente", "r", [], conversa_id=recente["id"])
        consultas.registrar_auditoria("login_ok", funcionario_id=f["id"], detalhe="auditoria antiga")
        consultas.registrar_auditoria("login_ok", funcionario_id=f["id"], detalhe="auditoria recente")

        velho_chat = dias_atras(200)
        _atualizar("chat_conversas", {"criado_em": velho_chat, "atualizado_em": velho_chat}, id=antiga["id"])
        _atualizar("chat_mensagens", {"criado_em": velho_chat}, conversa_id=antiga["id"])
        _atualizar("chat_historico", {"criado_em": velho_chat}, pergunta="pergunta antiga", funcionario_id=f["id"])
        _atualizar("auditoria_acessos", {"criado_em": dias_atras(800)}, detalhe="auditoria antiga",
                   funcionario_id=f["id"])

        resultado = consultas.expurgar_dados_antigos(dias_chat=180, dias_auditoria=730)
        assert set(resultado) >= {"chat_historico", "chat_conversas", "chat_mensagens", "auditoria"}
        assert resultado["chat_conversas"] >= 1
        assert resultado["chat_mensagens"] >= 2
        assert resultado["chat_historico"] >= 1
        assert resultado["auditoria"] >= 1

        assert consultas.obter_conversa(antiga["id"], f["id"]) is None
        assert consultas.obter_conversa(recente["id"], f["id"]) is not None
        assert _linhas("SELECT id FROM chat_mensagens WHERE conversa_id = :c", c=antiga["id"]) == []
        perguntas = {l["pergunta"] for l in _linhas("SELECT pergunta FROM chat_historico WHERE funcionario_id = :f",
                                                      f=f["id"])}
        assert perguntas == {"pergunta recente"}
        detalhes = {i["detalhe"] for i in consultas.listar_auditoria(funcionario_id=f["id"])["data"]}
        assert detalhes == {"auditoria recente"}

        # Segunda execucao: nada mais a apagar.
        segunda = consultas.expurgar_dados_antigos(dias_chat=180, dias_auditoria=730)
        assert segunda["chat_conversas"] == segunda["chat_mensagens"] == segunda["chat_historico"] == 0
        assert segunda["auditoria"] == 0
