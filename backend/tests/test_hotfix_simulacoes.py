"""Regressoes da criacao de simulacoes."""


def test_criar_simulacao_devolve_registro_persistido(client):
    dados = {
        "valor_atual": 400.0,
        "valor_proposto": 320.0,
        "periodo_meses": 12,
        "indicacoes": 2,
    }
    resposta = client.post("/v1/simulacoes", json=dados)
    assert resposta.status_code == 201
    criado = resposta.json()
    assert criado["id"] > 0
    for campo, valor in dados.items():
        assert criado[campo] == valor


def test_criar_simulacao_invalida_retorna_422(client):
    resposta = client.post(
        "/v1/simulacoes",
        json={"valor_atual": -1, "valor_proposto": 300, "periodo_meses": 0, "indicacoes": 1},
    )
    assert resposta.status_code == 422


def test_consulta_sql_retorna_simulacao_ou_none(client, session_factory):
    from app.repositories.simulacao_repository import SqlSimulacaoRepository

    dados = {"valor_atual": 400, "valor_proposto": 320, "periodo_meses": 12, "indicacoes": 2}
    criada = client.post("/v1/simulacoes", json=dados)
    assert criada.status_code == 201
    repo = SqlSimulacaoRepository(session_factory)
    assert repo.buscar_por_id(criada.json()["id"]).model_dump(mode="json") == criada.json()
    assert repo.buscar_por_id(999999) is None
