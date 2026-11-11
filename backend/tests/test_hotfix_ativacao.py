"""Contratos de ativacao de clientes."""


def test_etapas_do_cliente_cadastrado(client, cliente_valido):
    criado = client.post("/v1/clientes", json=cliente_valido)
    assert criado.status_code == 201
    ident = criado.json()["id"]
    resposta = client.get(f"/v1/clientes/{ident}/ativacao/etapas")
    assert resposta.status_code == 200


def test_alteracao_da_etapa_preserva_acesso_publico_original(client, cliente_valido):
    criado = client.post("/v1/clientes", json=cliente_valido)
    assert criado.status_code == 201
    ident = criado.json()["id"]
    resposta = client.patch(f"/v1/clientes/{ident}/ativacao", json={"etapa_atual": 2})
    assert resposta.status_code == 200
    assert resposta.json()["etapa_atual"] == 2
    assert client.get(f"/v1/clientes/{ident}/ativacao").json()["etapa_atual"] == 2
