"""
Testes de integração (HTTP) das rotas /v1/auth e da dependência obter_usuario_atual.
"""
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.core.security import criar_token_acesso

USUARIO = {"nome": "Operadora Bulbe", "email": "operacao@bulbe.com.br", "senha": "solar12345"}


def test_registrar_retorna_201_sem_senha(client: TestClient):
    resposta = client.post("/v1/auth/registrar", json=USUARIO)
    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo == {"id": 1, "nome": "Operadora Bulbe", "email": "operacao@bulbe.com.br"}


def test_registrar_email_duplicado_retorna_409(client: TestClient):
    client.post("/v1/auth/registrar", json=USUARIO)
    resposta = client.post("/v1/auth/registrar", json=USUARIO)
    assert resposta.status_code == 409
    assert resposta.json()["error"]["code"] == "EMAIL_JA_CADASTRADO"


@pytest.mark.parametrize(
    "campo, valor",
    [
        ("email", "email-sem-arroba"),
        ("senha", "curta"),
        ("nome", "ab"),
    ],
)
def test_registrar_dados_invalidos_retorna_422(client: TestClient, campo: str, valor: str):
    """Validações do Pydantic: email no formato errado, senha < 8 e nome < 3 caracteres."""
    resposta = client.post("/v1/auth/registrar", json={**USUARIO, campo: valor})
    assert resposta.status_code == 422


def test_login_retorna_token_bearer(client: TestClient):
    client.post("/v1/auth/registrar", json=USUARIO)
    resposta = client.post(
        "/v1/auth/login",
        data={"username": USUARIO["email"], "password": USUARIO["senha"]},
    )
    assert resposta.status_code == 200
    assert resposta.json()["token_type"] == "bearer"
    assert resposta.json()["access_token"]


def test_login_senha_errada_retorna_401(client: TestClient):
    client.post("/v1/auth/registrar", json=USUARIO)
    resposta = client.post(
        "/v1/auth/login",
        data={"username": USUARIO["email"], "password": "senha-errada"},
    )
    assert resposta.status_code == 401
    assert resposta.json()["error"]["code"] == "CREDENCIAIS_INVALIDAS"


def test_me_com_token_valido(client: TestClient, headers_auth: dict):
    resposta = client.get("/v1/auth/me", headers=headers_auth)
    assert resposta.status_code == 200
    assert resposta.json()["email"] == "operacao@bulbe.com.br"


def test_me_sem_token_retorna_401(client: TestClient):
    resposta = client.get("/v1/auth/me")
    assert resposta.status_code == 401
    assert resposta.json() == {
        "error": {
            "code": "TOKEN_INVALIDO",
            "message": "Token ausente, invalido ou expirado.",
            "status": 401,
        }
    }


def test_me_com_token_invalido_retorna_401(client: TestClient):
    resposta = client.get("/v1/auth/me", headers={"Authorization": "Bearer token-falso"})
    assert resposta.status_code == 401
    assert resposta.json()["error"]["code"] == "TOKEN_INVALIDO"


def test_me_com_token_expirado_retorna_401(client: TestClient):
    client.post("/v1/auth/registrar", json=USUARIO)
    token = criar_token_acesso(USUARIO["email"], expira_em=timedelta(minutes=-1))
    resposta = client.get("/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resposta.status_code == 401


@pytest.mark.xfail(
    strict=True,
    reason=(
        "BUG: main.py registra dois exception_handler para ErroDeNegocio; o segundo "
        "(tratar_erro_usina) sobrescreve o primeiro e o header WWW-Authenticate se perde."
    ),
)
def test_resposta_401_tem_header_www_authenticate(client: TestClient):
    """O padrão OAuth2 pede o header WWW-Authenticate: Bearer nas respostas 401."""
    resposta = client.get("/v1/auth/me")
    assert resposta.headers.get("WWW-Authenticate") == "Bearer"
