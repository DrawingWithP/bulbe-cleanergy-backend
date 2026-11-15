"""Erros de transicao de cupom preservam o estado persistido."""

import pytest

from app.db.seed import ID_CUPOM_MARCOS, popular
from app.repositories.cupom_repository import SqlCupomRepository


@pytest.mark.parametrize("situacao", ["ativo", "expirado", "descartado"])
def test_situacao_nao_permitida_retorna_400_sem_alterar_cupom(client, session_factory, situacao):
    with session_factory() as sessao:
        popular(sessao)
    url = f"/v1/cupons/{ID_CUPOM_MARCOS}"
    antes = client.get(url).json()

    resposta = client.patch(url, json={"situacao": situacao})

    assert resposta.status_code == 400
    assert resposta.json() == {"error": {
        "code": "SITUACAO_INVALIDA",
        "message": "Apenas é permitido alterar a situação para 'salvo' ou 'usado'.",
        "status": 400,
    }}
    persistido = SqlCupomRepository(session_factory).buscar_por_id(ID_CUPOM_MARCOS)
    assert persistido.model_dump(mode="json") == antes


def test_cupom_usado_nao_pode_voltar_a_salvo(client, session_factory):
    with session_factory() as sessao:
        popular(sessao)
    url = f"/v1/cupons/{ID_CUPOM_MARCOS}"
    usado = client.patch(url, json={"situacao": "usado"})
    assert usado.status_code == 200
    assert usado.json()["usado_em"] is not None

    resposta = client.patch(url, json={"situacao": "salvo"})

    assert resposta.status_code == 409
    assert resposta.json() == {"error": {
        "code": "CUPOM_JA_UTILIZADO",
        "message": "Um cupom já utilizado não pode ter sua situação alterada.",
        "status": 409,
    }}
    persistido = SqlCupomRepository(session_factory).buscar_por_id(ID_CUPOM_MARCOS)
    assert persistido.model_dump(mode="json") == usado.json()
