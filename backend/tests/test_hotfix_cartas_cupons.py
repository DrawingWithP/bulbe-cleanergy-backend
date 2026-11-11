"""Comportamento preexistente de cartas e cupons sem token."""

from app.db.seed import ID_CARTA_MARCOS, ID_MARCOS, popular


def test_abertura_de_carta_sem_token_continua_permitida(client, session_factory):
    with session_factory() as session:
        popular(session)
    resposta = client.post(f"/v1/cartas/{ID_CARTA_MARCOS}/abertura")
    assert resposta.status_code == 201


def test_cupom_pode_ser_salvo_sem_token(client, session_factory):
    with session_factory() as session:
        popular(session)
    cupom_id = client.get(f"/v1/clientes/{ID_MARCOS}/cupons").json()["data"][0]["id"]
    resposta = client.patch(f"/v1/cupons/{cupom_id}", json={"situacao": "salvo"})
    assert resposta.status_code == 200
    assert resposta.json()["situacao"] == "salvo"


def test_descartar_cupom_sem_token_preserva_contrato(client, session_factory):
    from app.db.seed import ID_CUPOM_MARCOS
    with session_factory() as session:
        popular(session)
    resposta = client.delete(f"/v1/cupons/{ID_CUPOM_MARCOS}")
    assert resposta.status_code == 204
    assert resposta.content == b""
    assert client.get(f"/v1/cupons/{ID_CUPOM_MARCOS}").status_code == 404
