"""Regressoes de cadastro e consulta de adesoes."""


def test_adesoes_lista_inicial_vazia(client):
    resposta = client.get("/v1/adesoes")
    assert resposta.status_code == 200
    assert resposta.json() == []


def test_adesoes_ausente_retorna_404(client):
    assert client.get("/v1/adesoes/999999").status_code == 404


def test_adesoes_mutacoes_mantem_autenticacao_original(client):
    assert client.put("/v1/adesoes/999999", json={"nome": "Outro Nome"}).status_code == 401
    assert client.delete("/v1/adesoes/999999").status_code == 401


def test_cadastro_retorna_adesao_persistida(client, adesao_valida, session_factory):
    from app.repositories.adesao_repository import SqlAdesaoRepository

    resposta = client.post("/v1/adesoes", json=adesao_valida)
    assert resposta.status_code == 201
    criada = resposta.json()
    lida = SqlAdesaoRepository(session_factory).buscar_por_id(criada["id"])
    assert lida is not None
    assert lida.model_dump(mode="json") == criada
    assert client.get(f"/v1/adesoes/{criada['id']}").json() == criada
    assert client.get("/v1/adesoes").json() == [criada]
    assert client.post("/v1/adesoes", json=adesao_valida).status_code == 409
    assert len(client.get("/v1/adesoes").json()) == 1
