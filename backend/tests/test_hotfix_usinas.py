"""Regressoes de listagem e exclusao de usinas."""


def test_usina_criada_aparece_na_listagem(client, headers_auth, usina_valida):
    resposta = client.post("/v1/usinas", json=usina_valida, headers=headers_auth)
    assert resposta.status_code == 201
    listagem = client.get("/v1/usinas")
    assert listagem.status_code == 200
    assert [item["id"] for item in listagem.json()] == [resposta.json()["id"]]


def test_usina_exclusao_sem_token_mantem_401(client):
    assert client.delete("/v1/usinas/999999").status_code == 401


def test_remocao_em_memoria_retorna_false_quando_ausente(usina_valida):
    from app.domain.usina import UsinaCreate
    from app.repositories.usina_repository import InMemoryUsinaRepository

    repo = InMemoryUsinaRepository()
    assert repo.remover(999999) is False
    criada = repo.criar(UsinaCreate(**usina_valida))
    assert repo.remover(criada.id) is True
    assert repo.buscar_por_id(criada.id) is None
    assert repo.remover(criada.id) is False


def test_atualizacao_usina_ausente_preserva_erro(client, headers_auth):
    resposta = client.put("/v1/usinas/999999", json={"nome": "Usina Inexistente"}, headers=headers_auth)
    assert resposta.status_code == 404
    assert resposta.json()["error"] == {
        "code": "RECURSO_NAO_ENCONTRADO",
        "message": "Usina com id 999999 nao foi encontrada.", "status": 404,
    }
