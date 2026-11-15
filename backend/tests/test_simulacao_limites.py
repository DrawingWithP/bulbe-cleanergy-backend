"""Limites validos e arredondamento do simulador pela API e SQL."""

import pytest

from app.repositories.simulacao_repository import SqlSimulacaoRepository


@pytest.mark.parametrize("atual,proposto,meses,indicacoes,mensal,total", [
    (0.01, 0, 1, 0, 0.01, 0.01),
    (200, 200, 12, 2, 0, 100),
    (200, 0, 1, 0, 200, 200),
    (19.99, 16.9915, 12, 1, 3, 86),
])
def test_limites_validos_e_calculo_persistido(
    client, session_factory, atual, proposto, meses, indicacoes, mensal, total,
):
    resposta = client.post("/v1/simulacoes", json={
        "valor_atual": atual, "valor_proposto": proposto,
        "periodo_meses": meses, "indicacoes": indicacoes, "bandeira": "verde",
    })

    assert resposta.status_code == 201
    dados = resposta.json()
    assert dados["economia_mensal"] == mensal
    assert dados["economia_total"] == total
    assert dados["cliente_id"] is None
    repo = SqlSimulacaoRepository(session_factory)
    persistida = repo.buscar_por_id(dados["id"])
    assert persistida is not None
    assert persistida.model_dump(mode="json") == dados
    assert len(repo.listar()) == 1
