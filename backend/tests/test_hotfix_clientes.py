"""Contratos de consulta e controle de acesso a clientes."""


def test_lista_clientes_vazia_e_paginacao(client):
    resposta = client.get("/v1/clientes")
    assert resposta.status_code == 200
    assert resposta.json()["total"] == 0
    assert client.get("/v1/clientes?page=0").status_code == 422


def test_atualizar_e_excluir_cliente_exigem_token(client):
    assert client.put("/v1/clientes/nao-existe", json={"nome": "Outro Nome"}).status_code == 401
    assert client.delete("/v1/clientes/nao-existe").status_code == 401
