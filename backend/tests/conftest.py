"""
Fixtures compartilhadas por todos os arquivos de teste.
O pytest encontra este arquivo sozinho; nao e preciso importa-lo.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.repositories.adesao_repository import adesao_repository
from app.repositories.ativacao_repository import ativacao_repository
from app.repositories.carta_repository import carta_repository
from app.repositories.cliente_repository import cliente_repository
from app.repositories.cupom_repository import cupom_repository
from app.repositories.dica_repository import dica_repository
from app.repositories.indicacao_repository import indicacao_repository
from app.repositories.parceiro_repository import parceiro_repository
from app.repositories.primeiro_acesso_repository import primeiro_acesso_repository
from app.repositories.simulacao_repository import simulacao_repository
from app.repositories.usina_repository import usina_repository
from app.repositories.usuario_repository import usuario_repository
from app.services.carta_service import carta_service

REPOSITORIOS_GLOBAIS = [
    adesao_repository,
    ativacao_repository,
    carta_repository,
    cliente_repository,
    cupom_repository,
    dica_repository,
    indicacao_repository,
    parceiro_repository,
    primeiro_acesso_repository,
    simulacao_repository,
    usina_repository,
    usuario_repository,
]


@pytest.fixture(autouse=True)
def limpar_repositorios():
    """
    Roda antes de CADA teste. Zera os repositorios em memoria (e o estado
    guardado no CartaService) para que um teste nunca dependa do que outro
    teste deixou para tras. Os repositorios que tem dados mock voltam
    ao estado inicial.
    """
    for repositorio in REPOSITORIOS_GLOBAIS:
        repositorio.__init__()
    carta_service.__init__(carta_repository)
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
