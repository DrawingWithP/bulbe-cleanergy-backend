"""
Chatbot do painel (secao 2 do contrato de melhorias) com a API da Anthropic SIMULADA
(ver tests/apoio.py): loop de ferramentas, mascaramento, erros do SDK, uso/custo,
conversas persistidas e reenviadas com conteudo identico, modo antigo e streaming SSE.
"""
import json
import re

import pytest
from sqlalchemy import text

from app.database import consultas
from app.database.conexao import engine
from tests.apoio import (
    conteudo_como_blocos,
    custo_esperado,
    datas_de_hoje_aceitas,
    ler_eventos_sse,
    resposta_erro,
    resposta_falha_conexao,
    resposta_ferramentas,
    resposta_texto,
    resultados_de_ferramenta,
    sem_nulos,
    texto_do_conteudo,
    texto_do_tool_result,
)

ROTA = "/v1/painel/chat"
ROTA_STREAM = "/v1/painel/chat/stream"
CHAVES_USO = {"input_tokens", "output_tokens", "cache_read_tokens", "cache_creation_tokens", "custo_estimado_usd"}
REGEX_CPF_MASCARADO = re.compile(r"\*\*\*\.\d{3}\.\d{3}-\*\*")


@pytest.fixture(scope="module")
def marcos() -> dict:
    return consultas.buscar_clientes(termo="MARCOS50")[0]


def _ultima_linha_historico(funcionario_id: int) -> dict:
    with engine.connect() as con:
        linha = con.execute(
            text("SELECT * FROM chat_historico WHERE funcionario_id = :f ORDER BY id DESC LIMIT 1"),
            {"f": funcionario_id},
        ).mappings().first()
    assert linha is not None, "A troca deveria ter sido registrada em chat_historico."
    return dict(linha)


def _mensagens_brutas(conversa_id: str) -> list[dict]:
    with engine.connect() as con:
        return [dict(l) for l in con.execute(
            text("SELECT * FROM chat_mensagens WHERE conversa_id = :c ORDER BY ordem"), {"c": conversa_id}
        ).mappings().all()]


def _confere_erro(corpo: dict, status: int) -> dict:
    assert set(corpo) == {"error"}, corpo
    erro = corpo["error"]
    assert erro["status"] == status and isinstance(erro["code"], str) and erro["code"] and erro["message"]
    return erro


def _stream(cliente_http, cabecalho: dict, corpo: dict):
    resposta = cliente_http.post(ROTA_STREAM, json=corpo, headers=cabecalho)
    return resposta, (ler_eventos_sse(resposta.text) if resposta.status_code == 200 else [])


# ---------------------------------------------------------------------------
# Disponibilidade e validacao
# ---------------------------------------------------------------------------
class TestDisponibilidade:
    def test_sem_chave_503(self, cliente_http, cab_atendimento, sem_chave_anthropic):
        resposta = cliente_http.post(ROTA, json={"mensagem": "Oi"}, headers=cab_atendimento)
        assert resposta.status_code == 503
        assert _confere_erro(resposta.json(), 503)["code"] == "CHATBOT_INDISPONIVEL"

    def test_sem_chave_stream(self, cliente_http, cab_atendimento, sem_chave_anthropic):
        resposta, eventos = _stream(cliente_http, cab_atendimento, {"mensagem": "Oi"})
        if resposta.status_code == 200:
            assert eventos and eventos[-1]["tipo"] == "erro"
            erro = eventos[-1]["error"]
            assert erro["code"] == "CHATBOT_INDISPONIVEL" and erro["status"] == 503
            assert not any(e["tipo"] == "fim" for e in eventos)
        else:
            assert resposta.status_code == 503
            assert _confere_erro(resposta.json(), 503)["code"] == "CHATBOT_INDISPONIVEL"

    def test_guarda_impede_cliente_real(self, guarda_anthropic):
        import anthropic

        with pytest.raises(RuntimeError):
            anthropic.Anthropic(api_key="qualquer")
        assert guarda_anthropic.tentativas == ["Anthropic"]
        guarda_anthropic.tentativas.clear()  # a tentativa aqui e proposital

    def test_sem_chave_nao_cria_cliente(self, cliente_http, cab_atendimento, sem_chave_anthropic,
                                        guarda_anthropic):
        cliente_http.post(ROTA, json={"mensagem": "Oi"}, headers=cab_atendimento)
        assert guarda_anthropic.tentativas == []

    def test_sugestoes(self, cliente_http, cab_atendimento):
        corpo = cliente_http.get(f"{ROTA}/sugestoes", headers=cab_atendimento).json()
        assert set(corpo) == {"sugestoes"}
        assert corpo["sugestoes"] and all(isinstance(s, str) and s for s in corpo["sugestoes"])

    @pytest.mark.parametrize("corpo", [{"mensagem": ""}, {"mensagem": "   "}, {"mensagem": "x" * 2001}, {}])
    def test_mensagem_invalida_422(self, cliente_http, cab_atendimento, api_anthropic, corpo):
        assert cliente_http.post(ROTA, json=corpo, headers=cab_atendimento).status_code == 422
        assert api_anthropic.chamadas == []


# ---------------------------------------------------------------------------
# Requisicao enviada a API
# ---------------------------------------------------------------------------
class TestRequisicaoParaApi:
    def test_resposta_simples_e_parametros(self, cliente_http, criar_funcionario, api_anthropic):
        f = criar_funcionario()
        api_anthropic.adicionar(resposta_texto("A Bulbe dá 15% de desconto."))
        resposta = cliente_http.post(ROTA, json={"mensagem": "Qual o desconto?"}, headers=f["cabecalho"])
        assert resposta.status_code == 200, resposta.text
        corpo = resposta.json()
        assert set(corpo) >= {"resposta", "ferramentas_usadas", "modelo", "conversa_id", "uso"}
        assert corpo["resposta"] == "A Bulbe dá 15% de desconto."
        assert corpo["ferramentas_usadas"] == []
        assert corpo["modelo"] == "claude-haiku-5-5"
        assert isinstance(corpo["conversa_id"], str) and corpo["conversa_id"]
        assert set(corpo["uso"]) >= CHAVES_USO

        assert len(api_anthropic.chamadas) == 1
        req = api_anthropic.chamadas[0]
        assert req["model"] == "claude-haiku-5-5"
        assert req["max_tokens"] > 0
        assert req.get("output_config", {}).get("effort") == "high"
        for proibido in ("temperature", "top_p", "top_k"):
            assert proibido not in req, f"'{proibido}' nao pode ser enviado ao Haiku 5.5"
        assert "budget_tokens" not in json.dumps(req.get("thinking", {}))
        if "tool_choice" in req:
            assert req["tool_choice"].get("type") == "auto"
        assert req["messages"][-1]["role"] == "user", "Sem prefill de assistant."
        nomes = {t["name"] for t in req["tools"]}
        assert {"buscar_clientes", "listar_clientes_parados", "resumo_ativacoes", "obter_cliente",
                "listar_faturas", "metricas_gerais", "simular_economia"} <= nomes
        buscar = next(t for t in req["tools"] if t["name"] == "buscar_clientes")
        assert "etapa" in buscar["input_schema"]["properties"]

    def test_contexto_vai_na_mensagem_e_nao_no_system(self, cliente_http, funcionario_ana, cab_ana, api_anthropic):
        api_anthropic.adicionar(resposta_texto("ok"))
        assert cliente_http.post(ROTA, json={"mensagem": "Bom dia"}, headers=cab_ana).status_code == 200
        req = api_anthropic.chamadas[0]
        primeira = texto_do_conteudo(req["messages"][0]["content"])
        assert "Bom dia" in primeira
        assert any(d in primeira for d in datas_de_hoje_aceitas()), primeira
        assert funcionario_ana["nome"].split()[0] in primeira
        system = json.dumps(req.get("system", ""), ensure_ascii=False)
        assert not any(d in system for d in datas_de_hoje_aceitas()), "A data de hoje saiu do system."

    def test_refusal_mensagem_amigavel(self, cliente_http, cab_atendimento, api_anthropic):
        api_anthropic.adicionar(resposta_texto("", stop_reason="refusal"))
        resposta = cliente_http.post(ROTA, json={"mensagem": "algo proibido"}, headers=cab_atendimento)
        assert resposta.status_code == 200
        assert resposta.json()["resposta"].strip()


# ---------------------------------------------------------------------------
# Loop de ferramentas e mascaramento
# ---------------------------------------------------------------------------
class TestFerramentas:
    def test_loop_com_duas_ferramentas(self, cliente_http, criar_funcionario, api_anthropic):
        f = criar_funcionario()
        api_anthropic.adicionar(
            resposta_ferramentas([("buscar_clientes", {"termo": "Marcos Andrade"}), ("metricas_gerais", {})],
                                 thinking="Preciso buscar o cliente e as métricas."),
            resposta_texto("O Marcos está na etapa 2."),
        )
        resposta = cliente_http.post(ROTA, json={"mensagem": "Em que etapa está o Marcos?"}, headers=f["cabecalho"])
        assert resposta.status_code == 200, resposta.text
        corpo = resposta.json()
        assert corpo["resposta"] == "O Marcos está na etapa 2."
        assert sorted(corpo["ferramentas_usadas"]) == ["buscar_clientes", "metricas_gerais"]

        assert len(api_anthropic.chamadas) == 2
        segunda = api_anthropic.chamadas[1]["messages"]
        primeira_resposta = api_anthropic.respostas_enviadas[0]
        assert segunda[-2]["role"] == "assistant"
        assert sem_nulos(conteudo_como_blocos(segunda[-2]["content"])) == primeira_resposta["content"], \
            "O conteudo do assistant (inclusive thinking) deve ser reenviado sem alteracao."
        assert segunda[-1]["role"] == "user"
        resultados = resultados_de_ferramenta(segunda[-1])
        assert len(resultados) == 2, "Todos os tool_result da volta numa unica mensagem user."
        ids_pedidos = [b["id"] for b in primeira_resposta["content"] if b["type"] == "tool_use"]
        assert [r["tool_use_id"] for r in resultados] == ids_pedidos
        assert not any(r.get("is_error") for r in resultados)
        assert "Marcos Andrade" in texto_do_tool_result(resultados[0])

    def test_mascara_cpf_e_telefone(self, cliente_http, cab_atendimento, api_anthropic, marcos):
        api_anthropic.adicionar(
            resposta_ferramentas([("buscar_clientes", {"termo": "MARCOS50"}),
                                  ("obter_cliente", {"cliente_id": marcos["id"]})]),
            resposta_texto("Pronto."),
        )
        assert cliente_http.post(ROTA, json={"mensagem": "Dados do Marcos"}, headers=cab_atendimento).status_code == 200
        enviado = json.dumps(api_anthropic.chamadas[1], ensure_ascii=False)
        cpf, telefone = marcos["cpf"], marcos["telefone"]
        cpf_formatado = f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"
        assert cpf not in enviado and cpf_formatado not in enviado, "CPF completo nao pode ir para o modelo."
        assert telefone not in enviado, "Telefone completo nao pode ir para o modelo."
        resultados = resultados_de_ferramenta(api_anthropic.chamadas[1]["messages"][-1])
        for resultado in resultados:
            assert REGEX_CPF_MASCARADO.search(texto_do_tool_result(resultado)), texto_do_tool_result(resultado)[:300]

    def test_ferramenta_invalida_vira_is_error(self, cliente_http, cab_atendimento, api_anthropic):
        api_anthropic.adicionar(
            resposta_ferramentas([("ferramenta_que_nao_existe", {}), ("obter_cliente", {})]),
            resposta_texto("Não consegui."),
        )
        resposta = cliente_http.post(ROTA, json={"mensagem": "teste"}, headers=cab_atendimento)
        assert resposta.status_code == 200
        resultados = resultados_de_ferramenta(api_anthropic.chamadas[1]["messages"][-1])
        assert len(resultados) == 2
        assert all(r.get("is_error") is True for r in resultados)

    def test_novas_ferramentas_executam(self, cliente_http, cab_atendimento, api_anthropic):
        api_anthropic.adicionar(
            resposta_ferramentas([("listar_clientes_parados", {"etapa": 2, "dias_minimos": 0}),
                                  ("resumo_ativacoes", {}),
                                  ("buscar_clientes", {"etapa": 2})]),
            resposta_texto("Resumo pronto."),
        )
        assert cliente_http.post(ROTA, json={"mensagem": "Quem está parado?"},
                                 headers=cab_atendimento).status_code == 200
        resultados = resultados_de_ferramenta(api_anthropic.chamadas[1]["messages"][-1])
        assert len(resultados) == 3
        assert not any(r.get("is_error") for r in resultados), [texto_do_tool_result(r)[:200] for r in resultados]
        assert "em_ativacao" in texto_do_tool_result(resultados[1])

    def test_faturas_trazem_bonus_clube(self, cliente_http, cab_atendimento, api_anthropic):
        with engine.connect() as con:
            cliente_id = con.execute(text("SELECT cliente_id FROM faturas WHERE bonus_clube > 0 LIMIT 1")).scalar()
        api_anthropic.adicionar(
            resposta_ferramentas([("listar_faturas", {"cliente_id": cliente_id})]),
            resposta_texto("ok"),
        )
        assert cliente_http.post(ROTA, json={"mensagem": "faturas"}, headers=cab_atendimento).status_code == 200
        resultado = resultados_de_ferramenta(api_anthropic.chamadas[1]["messages"][-1])[0]
        assert "bonus_clube" in texto_do_tool_result(resultado)

    def test_limite_de_8_voltas(self, cliente_http, cab_atendimento, api_anthropic):
        api_anthropic.padrao = resposta_ferramentas([("listar_dicas", {})])
        resposta = cliente_http.post(ROTA, json={"mensagem": "loop"}, headers=cab_atendimento)
        assert resposta.status_code == 200
        assert len(api_anthropic.chamadas) == 8
        assert resposta.json()["resposta"].strip()
        assert set(resposta.json()["ferramentas_usadas"]) == {"listar_dicas"}


# ---------------------------------------------------------------------------
# Erros do SDK
# ---------------------------------------------------------------------------
ERROS_API = [
    (resposta_erro(429, "rate_limit_error"), 429),
    (resposta_erro(400, "invalid_request_error"), 502),
    (resposta_erro(503, "api_error"), 503),
    (resposta_erro(529, "overloaded_error"), 503),
    (resposta_falha_conexao(), 503),
]


class TestErrosDaApi:
    @pytest.mark.parametrize("erro,status", ERROS_API)
    def test_post(self, cliente_http, cab_atendimento, api_anthropic, erro, status):
        api_anthropic.adicionar(erro)
        resposta = cliente_http.post(ROTA, json={"mensagem": "teste de erro"}, headers=cab_atendimento)
        assert resposta.status_code == status, resposta.text
        _confere_erro(resposta.json(), status)

    @pytest.mark.parametrize("erro,status", ERROS_API)
    def test_stream(self, cliente_http, cab_atendimento, api_anthropic, erro, status):
        api_anthropic.adicionar(erro)
        resposta, eventos = _stream(cliente_http, cab_atendimento, {"mensagem": "teste de erro"})
        assert resposta.status_code == 200, resposta.text
        assert eventos, resposta.text
        assert eventos[-1]["tipo"] == "erro", eventos
        erro_evento = eventos[-1]["error"]
        assert erro_evento["status"] == status and erro_evento["code"] and erro_evento["message"]
        assert not any(e["tipo"] == "fim" for e in eventos)
        if eventos[0]["tipo"] != "erro":
            assert eventos[0]["tipo"] == "inicio"

    def test_erro_no_meio_do_loop(self, cliente_http, cab_atendimento, api_anthropic):
        api_anthropic.adicionar(resposta_ferramentas([("listar_dicas", {})]), resposta_erro(429, "rate_limit_error"))
        resposta = cliente_http.post(ROTA, json={"mensagem": "dicas"}, headers=cab_atendimento)
        assert resposta.status_code == 429
        _confere_erro(resposta.json(), 429)


# ---------------------------------------------------------------------------
# Uso e custo
# ---------------------------------------------------------------------------
USO_VOLTA = {"input_tokens": 12_000, "output_tokens": 3_000,
             "cache_read_input_tokens": 5_000, "cache_creation_input_tokens": 800}


class TestUsoECusto:
    def test_uso_somado_e_custo(self, cliente_http, criar_funcionario, api_anthropic):
        f = criar_funcionario()
        api_anthropic.adicionar(
            resposta_ferramentas([("listar_dicas", {})], uso=USO_VOLTA),
            resposta_texto("Aqui estão as dicas.", uso=USO_VOLTA),
        )
        resposta = cliente_http.post(ROTA, json={"mensagem": "Dicas de economia"}, headers=f["cabecalho"])
        assert resposta.status_code == 200
        corpo = resposta.json()
        uso = corpo["uso"]
        assert uso["input_tokens"] == 24_000
        assert uso["output_tokens"] == 6_000
        assert uso["cache_read_tokens"] == 10_000
        assert uso["cache_creation_tokens"] == 1_600
        esperado = custo_esperado(24_000, 6_000, 10_000, 1_600)
        assert esperado == pytest.approx(0.0057)
        assert uso["custo_estimado_usd"] == pytest.approx(esperado, abs=1e-6)

        linha = _ultima_linha_historico(f["id"])
        assert "Dicas de economia" in linha["pergunta"]
        assert linha["resposta"] == "Aqui estão as dicas."
        assert json.loads(linha["ferramentas_usadas"]) == ["listar_dicas"]
        assert linha["conversa_id"] == corpo["conversa_id"]
        assert linha["modelo"] == "claude-haiku-5-5"
        assert linha["input_tokens"] == 24_000
        assert linha["output_tokens"] == 6_000
        assert linha["cache_read_tokens"] == 10_000
        assert linha["cache_creation_tokens"] == 1_600
        assert linha["custo_estimado_usd"] == pytest.approx(esperado, abs=1e-6)
        assert linha["duracao_ms"] is not None and linha["duracao_ms"] >= 0

    def test_uso_no_stream(self, cliente_http, criar_funcionario, api_anthropic):
        f = criar_funcionario()
        api_anthropic.adicionar(
            resposta_ferramentas([("listar_dicas", {})], uso=USO_VOLTA),
            resposta_texto("Dicas.", uso=USO_VOLTA),
        )
        _, eventos = _stream(cliente_http, f["cabecalho"], {"mensagem": "Dicas"})
        fim = eventos[-1]
        assert fim["tipo"] == "fim"
        assert fim["uso"]["input_tokens"] == 24_000
        assert fim["uso"]["output_tokens"] == 6_000
        assert fim["uso"]["cache_read_tokens"] == 10_000
        assert fim["uso"]["cache_creation_tokens"] == 1_600
        assert fim["uso"]["custo_estimado_usd"] == pytest.approx(0.0057, abs=1e-6)
        assert _ultima_linha_historico(f["id"])["custo_estimado_usd"] == pytest.approx(0.0057, abs=1e-6)


# ---------------------------------------------------------------------------
# Conversas persistidas no servidor
# ---------------------------------------------------------------------------
def _primeira_volta_com_ferramenta(api) -> None:
    api.adicionar(
        resposta_ferramentas([("buscar_clientes", {"termo": "Marcos Andrade"})],
                             thinking="Vou procurar o Marcos no cadastro."),
        resposta_texto("O Marcos Andrade está na etapa 2 (Documentos)."),
    )


class TestConversaPersistida:
    def test_segunda_pergunta_reenvia_historico_identico(self, cliente_http, criar_funcionario, api_anthropic):
        f = criar_funcionario()
        _primeira_volta_com_ferramenta(api_anthropic)
        r1 = cliente_http.post(ROTA, json={"mensagem": "Em que etapa está o Marcos Andrade?"}, headers=f["cabecalho"])
        assert r1.status_code == 200, r1.text
        conversa_id = r1.json()["conversa_id"]
        brutos_antes = _mensagens_brutas(conversa_id)
        assert len(brutos_antes) == 4  # user, assistant(tool_use), user(tool_result), assistant(texto)

        api_anthropic.adicionar(resposta_texto("A previsão é em até 90 dias."))
        r2 = cliente_http.post(ROTA, json={"mensagem": "E quando termina?", "conversa_id": conversa_id},
                               headers=f["cabecalho"])
        assert r2.status_code == 200, r2.text
        assert r2.json()["conversa_id"] == conversa_id

        volta1_chamada2 = api_anthropic.chamadas[1]
        volta2 = api_anthropic.chamadas[2]
        resposta_final_1 = api_anthropic.respostas_enviadas[1]["content"]
        esperado = [sem_nulos(m) for m in volta1_chamada2["messages"]]
        esperado.append({"role": "assistant", "content": resposta_final_1})
        enviados = volta2["messages"]
        assert len(enviados) == 5
        normalizar = lambda m: {"role": m["role"], "content": sem_nulos(conteudo_como_blocos(m["content"]))}  # noqa: E731
        assert [normalizar(m) for m in enviados[:4]] == [normalizar(m) for m in esperado], \
            "O historico deve ser reenviado exatamente como foi enviado/recebido."
        assert enviados[4]["role"] == "user"
        assert "E quando termina?" in texto_do_conteudo(enviados[4]["content"])

        # Prompt de sistema e ferramentas identicos byte a byte em toda a conversa.
        systems = {json.dumps(c.get("system"), ensure_ascii=False, sort_keys=False) for c in api_anthropic.chamadas}
        assert len(systems) == 1
        tools = {json.dumps(c.get("tools"), ensure_ascii=False, sort_keys=False) for c in api_anthropic.chamadas}
        assert len(tools) == 1

        # Historico so de acrescimo.
        brutos_depois = _mensagens_brutas(conversa_id)
        assert len(brutos_depois) == 6
        assert brutos_depois[:4] == brutos_antes

        # chat_historico ligado a conversa
        assert _ultima_linha_historico(f["id"])["conversa_id"] == conversa_id

    def test_historico_e_ignorado_com_conversa_id(self, cliente_http, criar_funcionario, api_anthropic):
        f = criar_funcionario()
        api_anthropic.adicionar(resposta_texto("primeira"), resposta_texto("segunda"))
        conversa_id = cliente_http.post(ROTA, json={"mensagem": "Olá"}, headers=f["cabecalho"]).json()["conversa_id"]
        corpo = {"mensagem": "De novo", "conversa_id": conversa_id,
                 "historico": [{"papel": "funcionario", "texto": "MARCADOR-QUE-NAO-PODE-IR"},
                               {"papel": "assistente", "texto": "outro marcador"}]}
        assert cliente_http.post(ROTA, json=corpo, headers=f["cabecalho"]).status_code == 200
        assert "MARCADOR-QUE-NAO-PODE-IR" not in json.dumps(api_anthropic.chamadas[1], ensure_ascii=False)
        assert len(api_anthropic.chamadas[1]["messages"]) == 3

    def test_modo_antigo_com_historico_de_texto(self, cliente_http, cab_atendimento, api_anthropic):
        api_anthropic.adicionar(resposta_texto("Resposta nova."))
        corpo = {"mensagem": "E o Clube?", "historico": [
            {"papel": "funcionario", "texto": "Como funciona a indicação?"},
            {"papel": "assistente", "texto": "Cada indicação vale R$ 50."},
        ]}
        resposta = cliente_http.post(ROTA, json=corpo, headers=cab_atendimento)
        assert resposta.status_code == 200, resposta.text
        assert resposta.json()["resposta"] == "Resposta nova."
        mensagens = api_anthropic.chamadas[0]["messages"]
        assert [m["role"] for m in mensagens] == ["user", "assistant", "user"]
        assert "Como funciona a indicação?" in texto_do_conteudo(mensagens[0]["content"])
        assert "Cada indicação vale R$ 50." in texto_do_conteudo(mensagens[1]["content"])
        assert "E o Clube?" in texto_do_conteudo(mensagens[2]["content"])

    def test_conversa_de_outro_funcionario(self, cliente_http, criar_funcionario, api_anthropic):
        dono, intruso = criar_funcionario(), criar_funcionario()
        api_anthropic.adicionar(resposta_texto("segredo do dono"))
        conversa_id = cliente_http.post(ROTA, json={"mensagem": "minha pergunta"},
                                        headers=dono["cabecalho"]).json()["conversa_id"]
        chamadas_antes = len(api_anthropic.chamadas)
        resposta = cliente_http.post(ROTA, json={"mensagem": "posso ver?", "conversa_id": conversa_id},
                                     headers=intruso["cabecalho"])
        assert resposta.status_code in (403, 404), resposta.text
        assert len(api_anthropic.chamadas) == chamadas_antes
        assert cliente_http.get(f"{ROTA}/conversas/{conversa_id}", headers=intruso["cabecalho"]).status_code == 404
        lista = cliente_http.get(f"{ROTA}/conversas", headers=intruso["cabecalho"]).json()["conversas"]
        assert conversa_id not in {c["id"] for c in lista}

    def test_rotas_de_conversas(self, cliente_http, criar_funcionario, api_anthropic):
        f = criar_funcionario()
        pergunta = "Quais clientes estão parados há mais de 30 dias na etapa de documentos da ativação?"
        _primeira_volta_com_ferramenta(api_anthropic)
        conversa_id = cliente_http.post(ROTA, json={"mensagem": pergunta}, headers=f["cabecalho"]).json()["conversa_id"]

        lista = cliente_http.get(f"{ROTA}/conversas", headers=f["cabecalho"])
        assert lista.status_code == 200
        conversas = lista.json()["conversas"]
        assert len(conversas) == 1
        item = conversas[0]
        assert set(item) >= {"id", "titulo", "criado_em", "atualizado_em", "total_mensagens"}
        assert item["id"] == conversa_id
        assert item["total_mensagens"] == 4
        assert 0 < len(item["titulo"]) <= 60
        assert pergunta.startswith(item["titulo"].rstrip("…. ").rstrip())

        detalhe = cliente_http.get(f"{ROTA}/conversas/{conversa_id}", headers=f["cabecalho"])
        assert detalhe.status_code == 200
        corpo = detalhe.json()
        assert corpo["id"] == conversa_id and corpo["titulo"] == item["titulo"]
        assert [m["papel"] for m in corpo["mensagens"]] == ["funcionario", "assistente"]
        assert corpo["mensagens"][0]["texto"].strip() == pergunta
        assert corpo["mensagens"][1]["texto"] == "O Marcos Andrade está na etapa 2 (Documentos)."
        assert cliente_http.get(f"{ROTA}/conversas/nao-existe", headers=f["cabecalho"]).status_code == 404


# ---------------------------------------------------------------------------
# Streaming (SSE)
# ---------------------------------------------------------------------------
class TestStream:
    def test_ordem_dos_eventos(self, cliente_http, criar_funcionario, api_anthropic):
        f = criar_funcionario()
        texto_final = "O Marcos Andrade está na etapa 2 (Documentos) e a previsão é dezembro."
        api_anthropic.adicionar(
            resposta_ferramentas([("buscar_clientes", {"termo": "Marcos Andrade"})], thinking="Buscar o Marcos."),
            resposta_texto(texto_final),
        )
        resposta, eventos = _stream(cliente_http, f["cabecalho"], {"mensagem": "Etapa do Marcos?"})
        assert resposta.status_code == 200, resposta.text
        assert resposta.headers["content-type"].startswith("text/event-stream")
        tipos = [e["tipo"] for e in eventos]
        assert tipos[0] == "inicio" and tipos[-1] == "fim", tipos
        assert set(tipos[1:-1]) <= {"ferramenta", "texto"}, tipos
        assert tipos.count("inicio") == 1 and tipos.count("fim") == 1

        inicio, fim = eventos[0], eventos[-1]
        assert inicio["conversa_id"] and fim["conversa_id"] == inicio["conversa_id"]
        ferramentas = [e["nome"] for e in eventos if e["tipo"] == "ferramenta"]
        assert ferramentas == ["buscar_clientes"]
        deltas = [e["delta"] for e in eventos if e["tipo"] == "texto"]
        assert len(deltas) > 1, "O texto deve chegar em pedacos."
        assert "".join(deltas).strip() == fim["resposta"].strip() == texto_final
        indice_ferramenta = tipos.index("ferramenta")
        assert indice_ferramenta < tipos.index("texto")
        assert set(fim) >= {"resposta", "ferramentas_usadas", "modelo", "conversa_id", "uso"}
        assert fim["ferramentas_usadas"] == ["buscar_clientes"]
        assert fim["modelo"] == "claude-haiku-5-5"
        assert set(fim["uso"]) >= CHAVES_USO

        # Usou streaming de verdade e ferramentas com eager_input_streaming.
        assert all(c.get("stream") is True for c in api_anthropic.chamadas)
        for ferramenta in api_anthropic.chamadas[0]["tools"]:
            if "input_schema" in ferramenta:
                assert ferramenta.get("eager_input_streaming") is True, ferramenta["name"]

        # Conversa persistida igual ao modo sem streaming.
        detalhe = cliente_http.get(f"{ROTA}/conversas/{inicio['conversa_id']}", headers=f["cabecalho"]).json()
        assert [m["texto"] for m in detalhe["mensagens"]] == ["Etapa do Marcos?", texto_final]
        assert len(_mensagens_brutas(inicio["conversa_id"])) == 4

    def test_stream_e_depois_post_reenvia_identico(self, cliente_http, criar_funcionario, api_anthropic):
        f = criar_funcionario()
        _primeira_volta_com_ferramenta(api_anthropic)
        _, eventos = _stream(cliente_http, f["cabecalho"], {"mensagem": "Etapa do Marcos Andrade?"})
        conversa_id = eventos[-1]["conversa_id"]
        api_anthropic.adicionar(resposta_texto("Segunda resposta."))
        r2 = cliente_http.post(ROTA, json={"mensagem": "E depois?", "conversa_id": conversa_id},
                               headers=f["cabecalho"])
        assert r2.status_code == 200, r2.text
        enviados = api_anthropic.chamadas[2]["messages"]
        normalizar = lambda m: {"role": m["role"], "content": sem_nulos(conteudo_como_blocos(m["content"]))}  # noqa: E731
        esperado = [normalizar(m) for m in api_anthropic.chamadas[1]["messages"]]
        esperado.append({"role": "assistant", "content": api_anthropic.respostas_enviadas[1]["content"]})
        assert [normalizar(m) for m in enviados[:4]] == esperado
        # O thinking acumulado do stream (texto + assinatura) volta intacto.
        thinking_original = api_anthropic.respostas_enviadas[0]["content"][0]
        assert thinking_original["type"] == "thinking"
        assert sem_nulos(conteudo_como_blocos(enviados[1]["content"]))[0] == thinking_original

    def test_stream_continua_conversa(self, cliente_http, criar_funcionario, api_anthropic):
        f = criar_funcionario()
        api_anthropic.adicionar(resposta_texto("um"), resposta_texto("dois"))
        _, e1 = _stream(cliente_http, f["cabecalho"], {"mensagem": "primeira"})
        conversa_id = e1[0]["conversa_id"]
        _, e2 = _stream(cliente_http, f["cabecalho"], {"mensagem": "segunda", "conversa_id": conversa_id})
        assert e2[0]["conversa_id"] == conversa_id and e2[-1]["tipo"] == "fim"
        assert len(api_anthropic.chamadas[1]["messages"]) == 3
        lista = cliente_http.get(f"{ROTA}/conversas", headers=f["cabecalho"]).json()["conversas"]
        assert [c["total_mensagens"] for c in lista if c["id"] == conversa_id] == [4]
