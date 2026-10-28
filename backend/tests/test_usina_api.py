"""
Testes de integração (HTTP) das rotas /v1/usinas.
POST, PUT e DELETE exigem token; GET é público.
"""
from fastapi.testclient import TestClient


def test_listar_usinas_e_publico(client: TestClient):
    resposta = client.get("/v1/usinas")
    assert resposta.status_code == 200
    assert resposta.json() == []


def test_criar_usina_sem_token_retorna_401(client: TestClient, usina_valida: dict):
    resposta = client.post("/v1/usinas", json=usina_valida)
    assert resposta.status_code == 401
    assert resposta.json()["error"]["code"] == "TOKEN_INVALIDO"


def test_criar_usina_com_token_retorna_201(client: TestClient, headers_auth: dict, usina_valida: dict):
    resposta = client.post("/v1/usinas", json=usina_valida, headers=headers_auth)
    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["id"] == 1
    assert corpo["status"] == "ativa"


def test_criar_usina_invalida_retorna_422(client: TestClient, headers_auth: dict, usina_valida: dict):
    resposta = client.post(
        "/v1/usinas", json={**usina_valida, "capacidade_geracao_kwh": 0}, headers=headers_auth
    )
    assert resposta.status_code == 422


def test_fluxo_completo_de_crud(client: TestClient, headers_auth: dict, usina_valida: dict):
    """Cria, consulta, atualiza e remove uma usina pela API."""
    client.post("/v1/usinas", json=usina_valida, headers=headers_auth)

    assert client.get("/v1/usinas/1").json()["nome"] == "Usina Solar Uberlandia"

    resposta_put = client.put("/v1/usinas/1", json={"status": "inativa"}, headers=headers_auth)
    assert resposta_put.status_code == 200
    assert resposta_put.json()["status"] == "inativa"

    resposta_delete = client.delete("/v1/usinas/1", headers=headers_auth)
    assert resposta_delete.status_code == 204
    assert client.get("/v1/usinas/1").status_code == 404


def test_buscar_usina_inexistente_retorna_erro_padronizado(client: TestClient):
    resposta = client.get("/v1/usinas/99")
    assert resposta.status_code == 404
    assert resposta.json() == {
        "error": {
            "code": "RECURSO_NAO_ENCONTRADO",
            "message": "Usina com id 99 nao foi encontrada.",
            "status": 404,
        }
    }


def test_atualizar_e_remover_sem_token_retornam_401(client: TestClient, headers_auth: dict, usina_valida: dict):
    client.post("/v1/usinas", json=usina_valida, headers=headers_auth)
    assert client.put("/v1/usinas/1", json={"nome": "Outra"}).status_code == 401
    assert client.delete("/v1/usinas/1").status_code == 401
    assert client.get("/v1/usinas/1").status_code == 200


def test_id_nao_numerico_retorna_422(client: TestClient):
    assert client.get("/v1/usinas/abc").status_code == 422
