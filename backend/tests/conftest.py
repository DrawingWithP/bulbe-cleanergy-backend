"""
Fixtures compartilhadas por todos os arquivos de teste.
O pytest encontra este arquivo sozinho; nao e preciso importa-lo.

- Testes unitarios (Services) usam os repositorios InMemory: nao tocam no banco.
- Testes de integracao (API e repositorios SQL) usam bulbe_test.db,
  recriado do zero antes de cada teste.
"""

import os

# A ORDEM IMPORTA: a variavel precisa existir antes de qualquer "from app ...",
# senao o engine e criado apontando para o bulbe.db de desenvolvimento
# e os testes apagariam os seus dados.
os.environ["BULBE_DATABASE_URL"] = "sqlite:///./bulbe_test.db"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import models  # noqa: E402,F401  (registra as tabelas no Base.metadata)
from app.db.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def banco_limpo():
    """
    Roda antes de CADA teste: apaga e recria todas as tabelas do banco de teste,
    para que um teste nunca dependa do que outro deixou para tras.
    (Na aplicacao o schema vem so das migrations; aqui o create_all e so para o teste.)
    """
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield


@pytest.fixture
def session_factory():
    """Fabrica de sessoes do banco de teste, para os testes dos repositorios SQL."""
    return SessionLocal


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


@pytest.fixture
def cliente_valido() -> dict:
    return {
        "nome": "Lucas Ferreira",
        "email": "lucas.ferreira@email.com",
        "cpf": "111.222.333-44",
        "telefone": "(31) 99999-8888",
        "endereco": {
            "cep": "30140-071",
            "logradouro": "Rua da Bahia",
            "numero": "500",
            "bairro": "Lourdes",
            "cidade": "Belo Horizonte",
            "uf": "MG",
        },
        "distribuidora": "CEMIG",
        "numero_instalacao": "4009876543",
    }
