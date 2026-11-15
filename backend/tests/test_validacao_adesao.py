"""Entradas rejeitadas nao podem deixar adesoes no banco."""

import pytest
from sqlalchemy import func, select

from app.db.models import AdesaoModel


@pytest.mark.parametrize("campo,valor", [
    ("nome", "Jo"),
    ("cpf", "1234567890"),
    ("telefone", "1234567"),
    ("cep", "30130"),
    ("numero", 0),
    ("uf", "MIN"),
    ("valor_conta_atual", 0),
    ("status", "inexistente"),
])
def test_adesao_invalida_nao_persiste(client, adesao_valida, session_factory, campo, valor):
    resposta = client.post("/v1/adesoes", json={**adesao_valida, campo: valor})

    assert resposta.status_code == 422
    assert any(erro["loc"] == ["body", campo] for erro in resposta.json()["detail"])
    with session_factory() as sessao:
        assert sessao.scalar(select(func.count()).select_from(AdesaoModel)) == 0
    assert client.get("/v1/adesoes").json() == []
