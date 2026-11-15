"""
Codigo de demonstracao do primeiro acesso: so fora de producao.
"""

from app.core import config
from app.db.seed import CPF_MARCOS, popular
from app.repositories.primeiro_acesso_repository import primeiro_acesso_repository


def test_codigo_de_demonstracao_fora_de_producao(client, session_factory):
    with session_factory() as session:
        popular(session)
    resposta = client.post("/v1/primeiro-acesso/verificacoes", json={"cpf": CPF_MARCOS})
    assert resposta.status_code == 202
    corpo = resposta.json()
    guardado = primeiro_acesso_repository.buscar_verificacao_por_id(corpo["verificacao_id"])
    assert corpo["codigo_demonstracao"] == guardado.codigo

    confirmacao = client.post(
        "/v1/primeiro-acesso/confirmacoes",
        json={"verificacao_id": corpo["verificacao_id"], "codigo": corpo["codigo_demonstracao"]},
    )
    assert confirmacao.status_code == 201


def test_producao_nao_devolve_o_codigo(client, session_factory, monkeypatch):
    with session_factory() as session:
        popular(session)
    monkeypatch.setattr(config, "AMBIENTE", "producao")
    resposta = client.post("/v1/primeiro-acesso/verificacoes", json={"cpf": CPF_MARCOS})
    assert resposta.status_code == 202
    assert resposta.json()["codigo_demonstracao"] is None
