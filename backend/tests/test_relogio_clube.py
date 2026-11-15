"""
Relogio de demonstracao e Clube Bulbe ao longo das semanas.
"""

from app.core import config
from app.db.seed import ID_CARTA_MARCOS, ID_CUPOM_MARCOS, ID_MARCOS, popular


def _popular(session_factory):
    with session_factory() as session:
        popular(session)


def _avancar(client, headers, dias):
    resposta = client.post("/v1/demonstracao/relogio/avancar", json={"dias": dias}, headers=headers)
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


# ---------------------------------------------------------------- relogio


def test_relogio_comeca_na_data_real(client):
    estado = client.get("/v1/demonstracao/relogio").json()
    assert estado["modo_demonstracao"] is True
    assert estado["dias_adiantados"] == 0


def test_avancar_e_resetar(client, headers_auth):
    inicio = client.get("/v1/demonstracao/relogio").json()["hoje"]
    estado = _avancar(client, headers_auth, 7)
    assert estado["dias_adiantados"] == 7
    assert estado["hoje"] > inicio

    resetado = client.post("/v1/demonstracao/relogio/resetar", headers=headers_auth).json()
    assert resetado["dias_adiantados"] == 0
    assert resetado["hoje"] == inicio


def test_avancar_exige_token_e_dias_validos(client, headers_auth):
    assert client.post("/v1/demonstracao/relogio/avancar", json={"dias": 1}).status_code == 401
    assert client.post("/v1/demonstracao/relogio/avancar", json={"dias": 0}, headers=headers_auth).status_code == 422
    assert client.post("/v1/demonstracao/relogio/avancar", json={"dias": 61}, headers=headers_auth).status_code == 422


def test_relogio_indisponivel_em_producao(client, headers_auth, monkeypatch):
    monkeypatch.setattr(config, "AMBIENTE", "producao")
    resposta = client.post("/v1/demonstracao/relogio/avancar", json={"dias": 1}, headers=headers_auth)
    assert resposta.status_code == 404
    assert resposta.json()["error"]["code"] == "DEMONSTRACAO_INDISPONIVEL"
    assert client.get("/v1/demonstracao/relogio").json()["modo_demonstracao"] is False


# ---------------------------------------------------------------- Clube ao longo das semanas


def test_proxima_carta_libera_com_o_relogio(client, session_factory, headers_auth):
    _popular(session_factory)
    abertura = client.post(f"/v1/cartas/{ID_CARTA_MARCOS}/abertura").json()
    assert abertura["semanas_sequencia"] == 4

    clube = client.get(f"/v1/clientes/{ID_MARCOS}/clube").json()
    assert clube["carta_disponivel"] is False
    assert clube["proxima_carta"]["dias_restantes"] == 7
    proxima_id = clube["proxima_carta"]["carta_id"]

    _avancar(client, headers_auth, 3)
    clube = client.get(f"/v1/clientes/{ID_MARCOS}/clube").json()
    assert clube["carta_disponivel"] is False
    assert clube["proxima_carta"]["dias_restantes"] == 4

    _avancar(client, headers_auth, 4)
    clube = client.get(f"/v1/clientes/{ID_MARCOS}/clube").json()
    assert clube["carta_disponivel"] is True
    assert clube["proxima_carta"]["carta_id"] == proxima_id
    assert client.post(f"/v1/cartas/{proxima_id}/abertura").status_code == 201


def test_carta_especial_da_50_reais_e_reinicia_a_sequencia(client, session_factory, headers_auth):
    _popular(session_factory)
    carta_id = ID_CARTA_MARCOS
    tipos = []
    for _ in range(2):  # Marcos comeca com 3 semanas: duas aberturas levam a 5
        abertura = client.post(f"/v1/cartas/{carta_id}/abertura").json()
        _avancar(client, headers_auth, 7)
        clube = client.get(f"/v1/clientes/{ID_MARCOS}/clube").json()
        carta_id = clube["proxima_carta"]["carta_id"]
        tipos.append(client.get(f"/v1/cartas/{carta_id}").json()["tipo"])

    assert clube["semanas_sequencia"] == 5
    assert clube["bonus_especial_pendente"] is True
    assert tipos[-1] == "especial"

    especial = client.post(f"/v1/cartas/{carta_id}/abertura").json()
    assert especial["cupom"]["titulo"] == "R$ 50 de desconto na fatura"
    assert especial["cupom"]["parceiro"]["nome"] == "Bulbe Energia"
    assert especial["semanas_sequencia"] == 0

    clube = client.get(f"/v1/clientes/{ID_MARCOS}/clube").json()
    assert clube["bonus_especial_pendente"] is False


# ---------------------------------------------------------------- validade dos cupons


def test_cupom_conta_os_dias_e_expira(client, session_factory, headers_auth):
    _popular(session_factory)
    assert client.get(f"/v1/cupons/{ID_CUPOM_MARCOS}").json()["dias_restantes"] == 14

    _avancar(client, headers_auth, 10)
    assert client.get(f"/v1/cupons/{ID_CUPOM_MARCOS}").json()["dias_restantes"] == 4

    _avancar(client, headers_auth, 5)
    cupom = client.get(f"/v1/cupons/{ID_CUPOM_MARCOS}").json()
    assert cupom["situacao"] == "expirado"
    assert cupom["dias_restantes"] == 0

    lista = client.get(f"/v1/clientes/{ID_MARCOS}/cupons?situacao=expirado").json()
    assert [c["id"] for c in lista["data"]] == [ID_CUPOM_MARCOS]

    resposta = client.patch(f"/v1/cupons/{ID_CUPOM_MARCOS}", json={"situacao": "salvo"})
    assert resposta.status_code == 409
    assert resposta.json()["error"]["code"] == "CUPOM_EXPIRADO"
