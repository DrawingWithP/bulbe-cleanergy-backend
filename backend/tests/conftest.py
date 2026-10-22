"""
Fixtures compartilhadas por todos os arquivos de teste.
O pytest encontra este arquivo sozinho; nao e preciso importa-lo.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.repositories.adesao_repository import adesao_repository

@pytest.fixture(autouse=True)
def limpar_repositorios():
    """
    Roda antes de CADA teste. Zera os repositorios em memoria para que
    um teste nunca dependa do que outro teste deixou para tras.
    """
    adesao_repository.__init__()
    yield

@pytest.fixture
def client() -> TestClient:
    """Cliente HTTP que chama a API sem precisar subir o uvicorn."""
    return TestClient(app)

@pytest.fixture
def headers_auth(client: TestClient) -> dict:
    """Cadastra um usuario, faz login e devolve o cabecalho Authorization."""
    client.post(
        "/v1/auth/registrar",
        json={"nome": "Operadora Bulbe", "email": "operacao@bulbe.com.br", "senha": "solar12345"},
    )
    resposta = client.post(
        "/v1/auth/login",
        data={"username": "operacao@bulbe.com.br", "password": "solar12345"},
    )
    token = resposta.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def usina_valida() -> dict:
    return {
        "nome": "Usina Solar Uberlandia",
        "localizacao": "Uberlandia, MG",
        "capacidade_geracao_kwh": 5000,
    }

