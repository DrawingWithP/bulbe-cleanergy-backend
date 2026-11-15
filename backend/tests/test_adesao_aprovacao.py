"""
Aprovar ou recusar adesao (sistema de gerenciamento): aprovar cria o cliente.
"""

from app.db.seed import CPF_ADESAO, popular


def _adesao_seed(client, session_factory):
    with session_factory() as session:
        popular(session)
    return next(a for a in client.get("/v1/adesoes").json() if a["cpf"] == CPF_ADESAO)


def test_aprovar_cria_o_cliente_e_a_jornada(client, session_factory, headers_auth):
    adesao = _adesao_seed(client, session_factory)
    resposta = client.post(f"/v1/adesoes/{adesao['id']}/aprovacao", headers=headers_auth)
    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    assert corpo["adesao"]["status"] == "aprovada"

    cliente = client.get(f"/v1/clientes/{corpo['cliente_id']}").json()
    assert cliente["nome"] == adesao["nome"]
    assert cliente["status"] == "em_ativacao"
    assert client.get(f"/v1/clientes/{corpo['cliente_id']}/ativacao").json()["etapa_atual"] == 1

    # O novo cliente ja consegue fazer o primeiro acesso com o CPF
    assert client.post("/v1/primeiro-acesso/verificacoes", json={"cpf": CPF_ADESAO}).status_code == 202


def test_adesao_ja_analisada_nao_muda(client, session_factory, headers_auth):
    adesao = _adesao_seed(client, session_factory)
    assert client.post(f"/v1/adesoes/{adesao['id']}/recusa", headers=headers_auth).json()["status"] == "recusada"
    resposta = client.post(f"/v1/adesoes/{adesao['id']}/aprovacao", headers=headers_auth)
    assert resposta.status_code == 409
    assert resposta.json()["error"]["code"] == "ADESAO_JA_ANALISADA"


def test_aprovacao_exige_token_e_adesao_existente(client, session_factory, headers_auth):
    adesao = _adesao_seed(client, session_factory)
    assert client.post(f"/v1/adesoes/{adesao['id']}/aprovacao").status_code == 401
    assert client.post("/v1/adesoes/999999/aprovacao", headers=headers_auth).status_code == 404
