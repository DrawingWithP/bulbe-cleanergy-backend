"""Regressoes de busca e listagem de indicacoes."""


def test_indicacao_criada_pode_ser_buscada_e_listada(client):
    criada = client.post(
        "/v1/indicacoes",
        json={"cliente_id": 1, "nome": "Maria Silva", "contato": "maria.teste@example.com"},
    )
    assert criada.status_code == 201
    identificador = criada.json()["id"]
    busca = client.get(f"/v1/indicacoes/{identificador}")
    assert busca.status_code == 200
    assert busca.json()["id"] == identificador
    lista = client.get("/v1/clientes/1/indicacoes")
    assert lista.status_code == 200
    assert [item["id"] for item in lista.json()] == [identificador]


def test_indicacao_ausente_retorna_404(client):
    assert client.get("/v1/indicacoes/999999").status_code == 404
