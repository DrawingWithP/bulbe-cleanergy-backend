"""
Testes de integração (HTTP) das rotas /v1/adesoes.
PUT e DELETE exigem token; GET e POST são públicos.
"""
import pytest
from fastapi.testclient import TestClient

ADESAO = {
    "nome": "João da Silva",
    "email": "joaosilva@gmail.com",
    "cpf": "14444444444",
    "telefone": "999999999",
    "cep": "34331312",
    "logradouro": "Rua Oliveira",
    "numero": 213,
    "bairro": "Buritis",
    "cidade": "Belo Horizonte",
    "uf": "MG",
    "distribuidora": "Cemig",
    "numero_instalacao": "3242412",
    "valor_conta_atual": 399.00,
}

ATUALIZACAO = {
    "nome": "João da Silva",
    "email": "joaosilva@gmail.com",
    "cpf": "14444444444",
    "telefone": "988888888",
    "status": "aprovada",
}


@pytest.fixture
def adesao_criada(client: TestClient) -> dict:
    return client.post("/v1/adesoes", json=ADESAO).json()


def test_criar_adesao_retorna_201(client: TestClient):
    resposta = client.post("/v1/adesoes", json=ADESAO)
    assert resposta.status_code == 201
    assert resposta.json()["id"] == 1
    assert resposta.json()["status"] == "enviada"


def test_criar_adesao_cpf_duplicado_retorna_409(client: TestClient, adesao_criada: dict):
    resposta = client.post("/v1/adesoes", json=ADESAO)
    assert resposta.status_code == 409
    assert resposta.json()["error"]["status"] == 409


def test_criar_adesao_invalida_retorna_422(client: TestClient):
    assert client.post("/v1/adesoes", json={**ADESAO, "uf": "MGS"}).status_code == 422


def test_listar_e_buscar_adesao(client: TestClient, adesao_criada: dict):
    assert len(client.get("/v1/adesoes").json()) == 1
    assert client.get("/v1/adesoes/1").json()["cpf"] == "14444444444"


def test_buscar_adesao_inexistente_retorna_404(client: TestClient):
    resposta = client.get("/v1/adesoes/99")
    assert resposta.status_code == 404
    assert resposta.json()["error"]["code"] == "RECURSO_NAO_ENCONTRADO"


def test_atualizar_adesao_sem_token_retorna_401(client: TestClient, adesao_criada: dict):
    assert client.put("/v1/adesoes/1", json=ATUALIZACAO).status_code == 401


def test_atualizar_adesao_com_token(client: TestClient, headers_auth: dict, adesao_criada: dict):
    resposta = client.put("/v1/adesoes/1", json=ATUALIZACAO, headers=headers_auth)
    assert resposta.status_code == 200
    assert resposta.json()["status"] == "aprovada"
    assert resposta.json()["telefone"] == "988888888"


def test_remover_adesao_sem_token_retorna_401(client: TestClient, adesao_criada: dict):
    assert client.delete("/v1/adesoes/1").status_code == 401


def test_remover_adesao_com_token_retorna_204(client: TestClient, headers_auth: dict, adesao_criada: dict):
    assert client.delete("/v1/adesoes/1", headers=headers_auth).status_code == 204
    assert client.get("/v1/adesoes/1").status_code == 404


@pytest.mark.xfail(
    strict=True,
    reason="BUG: AdesaoUpdate exige nome, email, cpf e telefone; um PUT so com o status da 422.",
)
def test_atualizar_somente_o_status_da_adesao(client: TestClient, headers_auth: dict, adesao_criada: dict):
    resposta = client.put("/v1/adesoes/1", json={"status": "aprovada"}, headers=headers_auth)
    assert resposta.status_code == 200
