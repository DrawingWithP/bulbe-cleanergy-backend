"""Regressoes de busca e listagem de indicacoes."""

from app.db.seed import ID_ANA, ID_MARCOS, popular


def test_indicacao_criada_pode_ser_buscada_e_listada(client, session_factory):
    with session_factory() as session:
        popular(session)
    criada = client.post(
        "/v1/indicacoes",
        json={"cliente_id": ID_MARCOS, "nome": "Maria Silva", "contato": "maria.teste@example.com"},
    )
    assert criada.status_code == 201
    identificador = criada.json()["id"]
    busca = client.get(f"/v1/indicacoes/{identificador}")
    assert busca.status_code == 200
    assert busca.json()["id"] == identificador
    assert busca.json()["cliente_id"] == ID_MARCOS
    lista = client.get(f"/v1/clientes/{ID_MARCOS}/indicacoes")
    assert lista.status_code == 200
    assert [item["id"] for item in lista.json()] == [identificador]
    assert client.get(f"/v1/clientes/{ID_ANA}/indicacoes").json() == []


def test_indicacao_ausente_retorna_404(client):
    assert client.get("/v1/indicacoes/999999").status_code == 404


def test_indicacao_para_cliente_inexistente_retorna_404(client):
    resposta = client.post(
        "/v1/indicacoes",
        json={"cliente_id": "nao-existe", "nome": "Maria Silva", "contato": "maria@example.com"},
    )
    assert resposta.status_code == 404
    assert resposta.json()["error"]["code"] == "RECURSO_NAO_ENCONTRADO"
    assert client.get("/v1/clientes/nao-existe/indicacoes").status_code == 404


def test_remover_cliente_remove_as_indicacoes(client, session_factory, headers_auth):
    with session_factory() as session:
        popular(session)
    criada = client.post(
        "/v1/indicacoes",
        json={"cliente_id": ID_ANA, "nome": "Joana Lima", "contato": "joana@example.com"},
    )
    assert criada.status_code == 201
    assert client.delete(f"/v1/clientes/{ID_ANA}", headers=headers_auth).status_code == 204
    assert client.get(f"/v1/indicacoes/{criada.json()['id']}").status_code == 404
