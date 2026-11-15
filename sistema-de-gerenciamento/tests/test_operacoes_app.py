"""
Rotas de operacao do painel sobre o app (relogio, dicas, parceiros, catalogo e atendimento).

A API do app e simulada substituindo api_app.chamar: os testes conferem o que o painel
enviaria ao app e as regras de permissao/validacao do painel.
"""
import pytest

from app.database import conexao
from app.database.modelos import Atendimento, Cliente, Parceiro
from app.integracao import api_app, sincronizacao


@pytest.fixture
def api(monkeypatch):
    chamadas: list = []
    respostas: dict = {}

    def chamar_falso(metodo, caminho, corpo=None, *, autenticado=True, config=None):
        chamadas.append((metodo, caminho, corpo, autenticado))
        for (m, prefixo), resposta in respostas.items():
            if m == metodo and caminho.startswith(prefixo):
                if isinstance(resposta, Exception):
                    raise resposta
                return resposta
        return {}

    monkeypatch.setattr(api_app, "chamar", chamar_falso)
    monkeypatch.setattr(sincronizacao, "sincronizar_sem_erro", lambda: None)
    return chamadas, respostas


# ---------------------------------------------------------------- relogio


def test_relogio_admin_avanca_e_atendimento_nao(cliente_http, cab_admin, cab_atendimento, api):
    chamadas, respostas = api
    respostas[("POST", "/v1/demonstracao/relogio/avancar")] = {"dias_adiantados": 7}
    resposta = cliente_http.post("/v1/painel/demonstracao/relogio/avancar", json={"dias": 7}, headers=cab_admin)
    assert resposta.status_code == 200
    assert ("POST", "/v1/demonstracao/relogio/avancar", {"dias": 7}, True) in chamadas
    assert cliente_http.post("/v1/painel/demonstracao/relogio/avancar", json={"dias": 7},
                             headers=cab_atendimento).status_code == 403
    assert cliente_http.post("/v1/painel/demonstracao/relogio/avancar", json={"dias": 0},
                             headers=cab_admin).status_code == 422


def test_erro_do_app_vira_erro_do_painel(cliente_http, cab_admin, api):
    _, respostas = api
    respostas[("POST", "/v1/demonstracao/relogio/resetar")] = api_app.ErroApiApp(
        "DEMONSTRACAO_INDISPONIVEL", "Nao existe em producao.", 404)
    resposta = cliente_http.post("/v1/painel/demonstracao/relogio/resetar", headers=cab_admin)
    assert resposta.status_code == 404
    assert resposta.json()["error"]["code"] == "DEMONSTRACAO_INDISPONIVEL"


# ---------------------------------------------------------------- dicas


def test_vitrine_de_dicas(cliente_http, cab_admin, cab_atendimento, api):
    chamadas, respostas = api
    respostas[("GET", "/v1/dicas")] = [{"id": 1, "titulo": "Troque por LED", "em_exibicao": True}]
    respostas[("PUT", "/v1/dicas/vitrine")] = []
    listagem = cliente_http.get("/v1/painel/app/dicas", headers=cab_atendimento).json()
    assert listagem["dicas"][0]["titulo"] == "Troque por LED"
    assert "geladeira" in listagem["icones"]

    assert cliente_http.put("/v1/painel/app/dicas/vitrine", json={"dicas": [1, 2, 3, 4, 5]},
                            headers=cab_admin).status_code == 200
    assert ("PUT", "/v1/dicas/vitrine", {"dicas": [1, 2, 3, 4, 5]}, True) in chamadas
    assert cliente_http.put("/v1/painel/app/dicas/vitrine", json={"dicas": [1, 2, 3]},
                            headers=cab_admin).status_code == 422
    assert cliente_http.put("/v1/painel/app/dicas/vitrine", json={"dicas": [1, 2, 3, 4, 5]},
                            headers=cab_atendimento).status_code == 403


def test_nova_dica_valida_o_icone(cliente_http, cab_admin, api):
    chamadas, _ = api
    dica = {"titulo": "Desligue a TV", "descricao": "TV em stand-by gasta.", "economia": 5, "icone": "televisao"}
    assert cliente_http.post("/v1/painel/app/dicas", json=dica, headers=cab_admin).status_code == 201
    assert chamadas[-1][:3] == ("POST", "/v1/dicas", dica)
    assert cliente_http.post("/v1/painel/app/dicas", json={**dica, "icone": "foguete"},
                             headers=cab_admin).status_code == 422


# ---------------------------------------------------------------- parceiros e catalogo


@pytest.fixture
def parceiro_do_app():
    """Um parceiro do painel vinculado ao app (id_app) e outro so ficticio."""
    with conexao.obter_sessao() as sessao:
        vinculado = Parceiro(id="parc-teste-app", nome="Parceiro Teste App", categoria="Teste",
                             id_app="parc-no-app", importado_do_app=True)
        ficticio = Parceiro(id="parc-teste-fict", nome="Parceiro Teste Ficticio", categoria="Teste")
        sessao.add_all([vinculado, ficticio])
    yield
    with conexao.obter_sessao() as sessao:
        for pid in ("parc-teste-app", "parc-teste-fict"):
            linha = sessao.get(Parceiro, pid)
            if linha is not None:
                sessao.delete(linha)


def test_catalogo_usa_o_id_do_parceiro_no_app(cliente_http, cab_admin, api, parceiro_do_app):
    chamadas, _ = api
    modelo = {"parceiro_id": "parc-teste-app", "titulo": "20% de desconto", "descricao": "Desconto na loja.",
              "prefixo_codigo": "TESTE20"}
    assert cliente_http.post("/v1/painel/catalogo-cupons", json=modelo, headers=cab_admin).status_code == 201
    assert chamadas[-1][1] == "/v1/catalogo-cupons"
    assert chamadas[-1][2]["parceiro_id"] == "parc-no-app"

    ficticio = cliente_http.post("/v1/painel/catalogo-cupons", json={**modelo, "parceiro_id": "parc-teste-fict"},
                                 headers=cab_admin)
    assert ficticio.status_code == 409
    assert ficticio.json()["error"]["code"] == "PARCEIRO_SEM_VINCULO_APP"
    assert cliente_http.post("/v1/painel/catalogo-cupons", json={**modelo, "prefixo_codigo": "minusculo"},
                             headers=cab_admin).status_code == 422


def test_cadastrar_parceiro(cliente_http, cab_admin, cab_atendimento, api):
    chamadas, _ = api
    novo = {"nome": "Cinema Bulbe", "categoria": "Lazer", "logo_url": None, "ativo": True}
    assert cliente_http.post("/v1/painel/parceiros", json=novo, headers=cab_admin).status_code == 201
    assert chamadas[-1][:3] == ("POST", "/v1/parceiros", novo)
    assert cliente_http.post("/v1/painel/parceiros", json=novo, headers=cab_atendimento).status_code == 403


# ---------------------------------------------------------------- atendimento


@pytest.fixture
def atendimento_do_app():
    with conexao.obter_sessao() as sessao:
        cliente = sessao.query(Cliente).first()
        atendimento = Atendimento(cliente_id=cliente.id, canal="app", assunto="Conversa pelo app",
                                  descricao="Oi", status="aberto", status_app="aguardando_atendente",
                                  id_app="atend-no-app", importado_do_app=True)
        sessao.add(atendimento)
        sessao.flush()
        ids = {"app": atendimento.id}
        ficticio = sessao.query(Atendimento).filter(Atendimento.id_app.is_(None)).first()
        ids["ficticio"] = ficticio.id
    yield ids
    with conexao.obter_sessao() as sessao:
        linha = sessao.get(Atendimento, ids["app"])
        if linha is not None:
            sessao.delete(linha)


def test_conversa_e_resposta_do_atendente(cliente_http, cab_atendimento, funcionario_atendimento, api,
                                          atendimento_do_app):
    chamadas, respostas = api
    respostas[("GET", "/v1/atendimentos/atend-no-app")] = {"status": "aguardando_atendente", "mensagens": []}
    conversa = cliente_http.get(f"/v1/painel/atendimentos/{atendimento_do_app['app']}/conversa?depois_de=3",
                                headers=cab_atendimento).json()
    assert conversa["atendimento"]["status_app"] == "aguardando_atendente"
    assert conversa["conversa"]["status"] == "aguardando_atendente"
    assert chamadas[-1][1] == "/v1/atendimentos/atend-no-app?depois_de=3"

    resposta = cliente_http.post(f"/v1/painel/atendimentos/{atendimento_do_app['app']}/respostas",
                                 json={"texto": "Oi! Vou te ajudar."}, headers=cab_atendimento)
    assert resposta.status_code == 201
    assert chamadas[-1][2] == {"texto": "Oi! Vou te ajudar.", "atendente": funcionario_atendimento["nome"]}


def test_atendimento_ficticio_nao_tem_chat(cliente_http, cab_atendimento, api, atendimento_do_app):
    conversa = cliente_http.get(f"/v1/painel/atendimentos/{atendimento_do_app['ficticio']}/conversa",
                                headers=cab_atendimento).json()
    assert conversa["conversa"] is None
    resposta = cliente_http.post(f"/v1/painel/atendimentos/{atendimento_do_app['ficticio']}/respostas",
                                 json={"texto": "Oi"}, headers=cab_atendimento)
    assert resposta.status_code == 409
    assert resposta.json()["error"]["code"] == "ATENDIMENTO_SEM_CHAT"
    assert cliente_http.get("/v1/painel/atendimentos/999999/conversa", headers=cab_atendimento).status_code == 404
