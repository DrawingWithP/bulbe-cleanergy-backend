"""Primeiro acesso: codigo invalido nao pode habilitar conta."""

from app.repositories.primeiro_acesso_repository import primeiro_acesso_repository


def test_codigo_incorreto_nao_habilita_acesso(client, cliente_valido):
    criado = client.post("/v1/clientes", json=cliente_valido)
    assert criado.status_code == 201
    ident = criado.json()["id"]
    resposta = client.post("/v1/primeiro-acesso/verificacoes", json={"cpf": "16899535009"})
    assert resposta.status_code == 202
    verificacao_id = resposta.json()["verificacao_id"]
    verificacao = primeiro_acesso_repository.buscar_verificacao_por_id(verificacao_id)
    errado = "000000" if verificacao.codigo != "000000" else "999999"
    falha = client.post(
        "/v1/primeiro-acesso/confirmacoes",
        json={"verificacao_id": verificacao_id, "codigo": errado},
    )
    assert falha.status_code == 400
    assert client.get(f"/v1/clientes/{ident}").json()["acesso_habilitado"] is False
