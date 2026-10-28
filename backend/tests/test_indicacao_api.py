"""
Testes de integração (HTTP) das rotas de Indicações.
Este controller usa HTTPException, então os erros vêm no formato {"detail": "..."}
e não no formato padronizado {"error": {...}} dos outros módulos.
"""
from fastapi.testclient import TestClient

from app.domain.indicacao import StatusIndicacao
from app.repositories.indicacao_repository import indicacao_repository

INDICACAO = {"cliente_id": 1, "nome": "Paula Mendes", "contato": "paula@email.com"}


def test_criar_indicacao_retorna_201(client: TestClient):
    resposta = client.post("/v1/indicacoes", json=INDICACAO)
    assert resposta.status_code == 201
    assert resposta.json()["situacao"] == "pendente"


def test_criar_indicacao_duplicada_retorna_409(client: TestClient):
    client.post("/v1/indicacoes", json=INDICACAO)
    resposta = client.post("/v1/indicacoes", json=INDICACAO)
    assert resposta.status_code == 409
    assert "ja possui uma indicacao" in resposta.json()["detail"]


def test_consultar_indicacao(client: TestClient):
    client.post("/v1/indicacoes", json=INDICACAO)
    resposta = client.get("/v1/indicacoes/1")
    assert resposta.status_code == 200
    assert resposta.json()["nome"] == "Paula Mendes"


def test_consultar_indicacao_inexistente_retorna_404(client: TestClient):
    resposta = client.get("/v1/indicacoes/99")
    assert resposta.status_code == 404
    assert resposta.json() == {"detail": "Indicacao nao encontrada."}


def test_listar_indicacoes_do_cliente(client: TestClient):
    client.post("/v1/indicacoes", json=INDICACAO)
    resposta = client.get("/v1/clientes/1/indicacoes")
    assert resposta.status_code == 200
    assert len(resposta.json()) == 1


def test_excluir_indicacao_sem_token_retorna_401(client: TestClient):
    client.post("/v1/indicacoes", json=INDICACAO)
    assert client.delete("/v1/indicacoes/1").status_code == 401


def test_excluir_indicacao_com_token_retorna_204(client: TestClient, headers_auth: dict):
    client.post("/v1/indicacoes", json=INDICACAO)
    assert client.delete("/v1/indicacoes/1", headers=headers_auth).status_code == 204
    assert client.get("/v1/indicacoes/1").status_code == 404


def test_excluir_indicacao_inexistente_retorna_404(client: TestClient, headers_auth: dict):
    assert client.delete("/v1/indicacoes/99", headers=headers_auth).status_code == 404


def test_excluir_indicacao_concluida_retorna_409(client: TestClient, headers_auth: dict):
    client.post("/v1/indicacoes", json=INDICACAO)
    indicacao_repository.buscar_por_id(1).situacao = StatusIndicacao.aderiu

    resposta = client.delete("/v1/indicacoes/1", headers=headers_auth)
    assert resposta.status_code == 409
