"""
Testes de integração (HTTP) das rotas /v1/dicas.
POST, PUT e DELETE exigem token; GET é público.
"""
import pytest
from fastapi.testclient import TestClient

DICA = {
    "titulo": "Desligue o ar-condicionado",
    "descricao": "Desligue o ar-condicionado ao sair do ambiente.",
    "economia": 35.5,
    "imagem_svg": "<svg></svg>",
}


@pytest.fixture
def dica_criada(client: TestClient, headers_auth: dict) -> dict:
    return client.post("/v1/dicas", json=DICA, headers=headers_auth).json()


def test_criar_dica_sem_token_retorna_401(client: TestClient):
    assert client.post("/v1/dicas", json=DICA).status_code == 401


def test_criar_dica_com_token_retorna_201(client: TestClient, headers_auth: dict):
    resposta = client.post("/v1/dicas", json=DICA, headers=headers_auth)
    assert resposta.status_code == 201
    assert resposta.json()["id"] == 1


def test_listar_e_buscar_dica_sao_publicos(client: TestClient, dica_criada: dict):
    assert len(client.get("/v1/dicas").json()) == 1
    assert client.get(f"/v1/dicas/{dica_criada['id']}").json()["titulo"] == DICA["titulo"]


def test_atualizar_dica(client: TestClient, headers_auth: dict, dica_criada: dict):
    resposta = client.put("/v1/dicas/1", json={"economia": 42}, headers=headers_auth)
    assert resposta.status_code == 200
    assert resposta.json()["economia"] == 42


def test_remover_dica_retorna_204(client: TestClient, headers_auth: dict, dica_criada: dict):
    """US-30: Remove a dica e ela deixa de existir."""
    assert client.delete("/v1/dicas/1", headers=headers_auth).status_code == 204
    assert client.get("/v1/dicas/1").status_code == 404


def test_atualizar_e_remover_sem_token_retornam_401(client: TestClient, dica_criada: dict):
    assert client.put("/v1/dicas/1", json={"economia": 42}).status_code == 401
    assert client.delete("/v1/dicas/1").status_code == 401


def test_remover_dica_inexistente_retorna_404(client: TestClient, headers_auth: dict):
    resposta = client.delete("/v1/dicas/99", headers=headers_auth)
    assert resposta.status_code == 404
    assert resposta.json()["error"]["code"] == "RECURSO_NAO_ENCONTRADO"
