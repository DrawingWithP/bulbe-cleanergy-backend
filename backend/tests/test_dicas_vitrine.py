"""
Dicas: icone pronto e vitrine de 5 dicas exibidas no app.
"""

from app.db.seed import DICAS, popular


def _popular(session_factory):
    with session_factory() as session:
        popular(session)


def _ids_por_titulo(client):
    return {d["titulo"]: d["id"] for d in client.get("/v1/dicas?todas=true").json()}


def test_app_recebe_so_as_5_da_vitrine_na_ordem(client, session_factory):
    _popular(session_factory)
    vitrine = client.get("/v1/dicas").json()
    assert [d["titulo"] for d in vitrine] == [titulo for titulo, *_ in DICAS[:5]]
    assert [d["ordem"] for d in vitrine] == [1, 2, 3, 4, 5]
    assert all(d["em_exibicao"] for d in vitrine)
    assert vitrine[0]["icone"] == "lampada_led"


def test_acervo_traz_todas_com_a_vitrine_primeiro(client, session_factory):
    _popular(session_factory)
    acervo = client.get("/v1/dicas?todas=true").json()
    assert len(acervo) == len(DICAS)
    assert [d["em_exibicao"] for d in acervo[:5]] == [True] * 5
    assert not any(d["em_exibicao"] for d in acervo[5:])


def test_trocar_a_vitrine(client, session_factory, headers_auth):
    _popular(session_factory)
    ids = _ids_por_titulo(client)
    nova = [ids["Aproveite a luz do sol"], ids["Troque por LED"], ids["Geladeira longe do fogão"],
            ids["Banhos rápidos"], ids["Ar-condicionado em 23 °C"]]
    resposta = client.put("/v1/dicas/vitrine", json={"dicas": nova}, headers=headers_auth)
    assert resposta.status_code == 200, resposta.text
    assert [d["id"] for d in client.get("/v1/dicas").json()] == nova


def test_vitrine_exige_5_dicas_diferentes_e_existentes(client, session_factory, headers_auth):
    _popular(session_factory)
    assert client.put("/v1/dicas/vitrine", json={"dicas": [1, 2, 3, 4]}, headers=headers_auth).status_code == 422
    repetida = client.put("/v1/dicas/vitrine", json={"dicas": [1, 1, 2, 3, 4]}, headers=headers_auth)
    assert repetida.status_code == 422
    assert repetida.json()["error"]["code"] == "VITRINE_INVALIDA"
    inexistente = client.put("/v1/dicas/vitrine", json={"dicas": [1, 2, 3, 4, 999]}, headers=headers_auth)
    assert inexistente.status_code == 422
    assert client.put("/v1/dicas/vitrine", json={"dicas": [1, 2, 3, 4, 5]}).status_code == 401


def test_dica_da_vitrine_nao_pode_ser_removida(client, session_factory, headers_auth):
    _popular(session_factory)
    primeira = client.get("/v1/dicas").json()[0]["id"]
    resposta = client.delete(f"/v1/dicas/{primeira}", headers=headers_auth)
    assert resposta.status_code == 409
    assert resposta.json()["error"]["code"] == "DICA_NA_VITRINE"


def test_criar_dica_com_icone_e_sem_svg(client, headers_auth):
    resposta = client.post("/v1/dicas", json={
        "titulo": "Desligue a TV da tomada", "descricao": "TV em stand-by gasta o mês inteiro.",
        "economia": 5, "icone": "televisao",
    }, headers=headers_auth)
    assert resposta.status_code == 201, resposta.text
    assert resposta.json()["icone"] == "televisao"
    assert resposta.json()["imagem_svg"] is None
    assert resposta.json()["em_exibicao"] is False
    invalido = client.post("/v1/dicas", json={
        "titulo": "Outra dica", "descricao": "Descricao.", "economia": 5, "icone": "foguete",
    }, headers=headers_auth)
    assert invalido.status_code == 422


def test_sem_vitrine_o_app_recebe_todas(client, headers_auth):
    """Compatibilidade: antes de montar a vitrine, GET /v1/dicas lista todas."""
    for titulo in ("Dica um", "Dica dois"):
        client.post("/v1/dicas", json={"titulo": titulo, "descricao": "Descricao.", "economia": 3},
                    headers=headers_auth)
    assert [d["titulo"] for d in client.get("/v1/dicas").json()] == ["Dica um", "Dica dois"]
