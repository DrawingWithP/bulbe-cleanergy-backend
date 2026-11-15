"""
Atendimento pelo app: robo de respostas automaticas, fila e atendente.
"""

from app.db.seed import ID_ANA, ID_MARCOS, popular
from app.services import atendimento_bot as bot


def _popular(session_factory):
    with session_factory() as session:
        popular(session)


def _abrir(client, cliente_id=ID_MARCOS):
    resposta = client.post("/v1/atendimentos", json={"cliente_id": cliente_id})
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _enviar(client, atendimento_id, texto):
    resposta = client.post(f"/v1/atendimentos/{atendimento_id}/mensagens", json={"texto": texto})
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


# ---------------------------------------------------------------- robo (unidade)


def test_robo_identifica_os_topicos():
    assert bot.identificar("Prazo da minha conexão") == "prazo"
    assert bot.identificar("quando a cemig libera?") == "prazo"
    assert bot.identificar("como pago o boleto") == "fatura"
    assert bot.identificar("quero falar com um atendente") == "atendente"
    assert bot.identificar("resolveu, obrigado!") == "resolveu"
    assert bot.identificar("asdfgh") is None


# ---------------------------------------------------------------- conversa com o robo


def test_abrir_conversa_traz_boas_vindas_com_opcoes(client, session_factory):
    _popular(session_factory)
    conversa = _abrir(client)
    assert conversa["status"] == "bot"
    [boas_vindas] = conversa["mensagens"]
    assert boas_vindas["autor"] == "bot"
    assert boas_vindas["texto"].startswith("Oi, Marcos!")
    assert bot.OPCAO_ATENDENTE in boas_vindas["opcoes"]


def test_robo_responde_com_os_dados_do_cliente(client, session_factory):
    _popular(session_factory)
    conversa = _abrir(client)
    novas = _enviar(client, conversa["id"], "Prazo da minha conexão")
    assert [m["autor"] for m in novas] == ["cliente", "bot"]
    assert "etapa 2 de 5" in novas[1]["texto"]
    assert novas[1]["opcoes"] == bot.OPCOES_DEPOIS

    clube = _enviar(client, conversa["id"], "Clube Bulbe e cupons")[1]["texto"]
    assert "3 de 5 semanas" in clube


def test_resolveu_encerra_a_conversa(client, session_factory):
    _popular(session_factory)
    conversa = _abrir(client)
    _enviar(client, conversa["id"], "Resolveu, obrigado!")
    detalhe = client.get(f"/v1/atendimentos/{conversa['id']}").json()
    assert detalhe["status"] == "resolvido"
    assert detalhe["encerrado_em"] is not None
    resposta = client.post(f"/v1/atendimentos/{conversa['id']}/mensagens", json={"texto": "oi"})
    assert resposta.status_code == 409
    assert resposta.json()["error"]["code"] == "ATENDIMENTO_ENCERRADO"


# ---------------------------------------------------------------- atendente real


def test_cliente_pede_atendente_e_operador_responde(client, session_factory, headers_auth):
    _popular(session_factory)
    conversa = _abrir(client)
    novas = _enviar(client, conversa["id"], "Falar com um atendente")
    assert novas[-1]["autor"] == "sistema"

    fila = client.get("/v1/atendimentos?status=aguardando_atendente", headers=headers_auth).json()
    # A conversa da Ana (seed) tambem esta na fila; a mais recente vem primeiro.
    assert fila[0]["id"] == conversa["id"]
    assert fila[0]["cliente_nome"] == "Marcos Andrade"
    assert {a["status"] for a in fila} == {"aguardando_atendente"}

    # Mensagem do cliente enquanto espera: o robo nao responde mais
    assert [m["autor"] for m in _enviar(client, conversa["id"], "Mudei de casa")] == ["cliente"]

    resposta = client.post(f"/v1/atendimentos/{conversa['id']}/respostas",
                           json={"texto": "Oi, Marcos! Vou te ajudar com a mudança.", "atendente": "Paula"},
                           headers=headers_auth)
    assert resposta.status_code == 201
    detalhe = client.get(f"/v1/atendimentos/{conversa['id']}").json()
    assert detalhe["status"] == "em_atendimento"
    assert detalhe["atendente_nome"] == "Paula"
    assert [m["autor"] for m in detalhe["mensagens"][-2:]] == ["sistema", "atendente"]


def test_polling_com_depois_de(client, session_factory):
    _popular(session_factory)
    conversa = _abrir(client)
    ultima = conversa["mensagens"][-1]["id"]
    _enviar(client, conversa["id"], "Minha conta de luz")
    novas = client.get(f"/v1/atendimentos/{conversa['id']}?depois_de={ultima}").json()["mensagens"]
    assert [m["autor"] for m in novas] == ["cliente", "bot"]


def test_encerrar_com_avaliacao(client, session_factory):
    _popular(session_factory)
    conversa = _abrir(client)
    detalhe = client.post(f"/v1/atendimentos/{conversa['id']}/encerramento", json={"avaliacao": 5}).json()
    assert detalhe["status"] == "resolvido"
    assert detalhe["avaliacao"] == 5
    assert client.post(f"/v1/atendimentos/{conversa['id']}/encerramento", json={"avaliacao": 9}).status_code == 422


def test_conversas_do_cliente_e_validacoes(client, session_factory, headers_auth):
    _popular(session_factory)
    _abrir(client, ID_ANA)
    _abrir(client, ID_MARCOS)
    # 1 do seed (mudanca de endereco) + a aberta agora
    assert len(client.get(f"/v1/clientes/{ID_ANA}/atendimentos").json()) == 2
    assert client.post("/v1/atendimentos", json={"cliente_id": "nao-existe"}).status_code == 404
    assert client.get("/v1/atendimentos").status_code == 401
    assert client.get("/v1/atendimentos/nao-existe").status_code == 404
    conversa = _abrir(client)
    assert client.post(f"/v1/atendimentos/{conversa['id']}/mensagens", json={"texto": ""}).status_code == 422
    assert client.post(f"/v1/atendimentos/{conversa['id']}/respostas", json={"texto": "oi", "atendente": "Paula"}
                       ).status_code == 401
