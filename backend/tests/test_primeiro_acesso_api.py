"""
Testes de integração (HTTP) das rotas de Primeiro Acesso (US-09 e US-10).
"""
import pytest
from fastapi.testclient import TestClient

from app.repositories.primeiro_acesso_repository import primeiro_acesso_repository

CLIENTE_ID_PADRAO = "8f1c2a6e-4b7d-4c1a-9f52-3d6a1b0c7e11"


def _solicitar(client: TestClient, cpf: str = "123.456.789-00") -> dict:
    return client.post("/v1/primeiro-acesso/verificacoes", json={"cpf": cpf, "canal": "sms"}).json()


def test_solicitar_verificacao_retorna_202(client: TestClient):
    """US-09: O código é enviado e a resposta mostra só o destino mascarado."""
    resposta = client.post("/v1/primeiro-acesso/verificacoes", json={"cpf": "123.456.789-00"})
    assert resposta.status_code == 202
    assert resposta.json()["destino_mascarado"] == "(31) *****-1234"
    assert "codigo" not in resposta.json()


def test_solicitar_verificacao_cpf_invalido_retorna_400(client: TestClient):
    resposta = client.post("/v1/primeiro-acesso/verificacoes", json={"cpf": "123"})
    assert resposta.status_code == 400
    assert resposta.json()["error"]["code"] == "CPF_INVALIDO"


def test_solicitar_verificacao_cpf_nao_cadastrado_retorna_404(client: TestClient):
    resposta = client.post("/v1/primeiro-acesso/verificacoes", json={"cpf": "999.888.777-66"})
    assert resposta.status_code == 404
    assert resposta.json()["error"]["code"] == "CLIENTE_NAO_ENCONTRADO"


def test_solicitar_verificacao_canal_invalido_retorna_422(client: TestClient):
    resposta = client.post(
        "/v1/primeiro-acesso/verificacoes", json={"cpf": "12345678900", "canal": "telegram"}
    )
    assert resposta.status_code == 422


def test_fluxo_completo_de_primeiro_acesso(client: TestClient):
    """US-09 + US-10: Solicita o código, confirma e recebe 201 com o acesso habilitado."""
    verificacao = _solicitar(client)
    codigo = primeiro_acesso_repository.buscar_verificacao_por_id(verificacao["verificacao_id"]).codigo

    resposta = client.post(
        "/v1/primeiro-acesso/confirmacoes",
        json={"verificacao_id": verificacao["verificacao_id"], "codigo": codigo},
    )

    assert resposta.status_code == 201
    assert resposta.json()["cliente_id"] == CLIENTE_ID_PADRAO
    assert resposta.json()["acesso_habilitado"] is True


def test_confirmar_codigo_errado_retorna_400(client: TestClient):
    verificacao = _solicitar(client)
    resposta = client.post(
        "/v1/primeiro-acesso/confirmacoes",
        json={"verificacao_id": verificacao["verificacao_id"], "codigo": "000000"},
    )
    assert resposta.status_code == 400
    assert resposta.json()["error"]["code"] == "CODIGO_INVALIDO"


def test_confirmar_codigo_curto_demais_retorna_422(client: TestClient):
    """O código precisa ter entre 4 e 10 caracteres."""
    resposta = client.post(
        "/v1/primeiro-acesso/confirmacoes", json={"verificacao_id": "qualquer", "codigo": "12"}
    )
    assert resposta.status_code == 422


def test_confirmar_verificacao_inexistente_retorna_404(client: TestClient):
    resposta = client.post(
        "/v1/primeiro-acesso/confirmacoes", json={"verificacao_id": "nao-existe", "codigo": "123456"}
    )
    assert resposta.status_code == 404


@pytest.mark.xfail(
    strict=True,
    reason=(
        "BUG: o PrimeiroAcessoRepository tem sua propria lista de clientes; confirmar o "
        "codigo nao atualiza acesso_habilitado no ClienteRepository usado por /v1/clientes."
    ),
)
def test_confirmacao_reflete_no_cadastro_do_cliente(client: TestClient):
    verificacao = _solicitar(client)
    codigo = primeiro_acesso_repository.buscar_verificacao_por_id(verificacao["verificacao_id"]).codigo
    client.post(
        "/v1/primeiro-acesso/confirmacoes",
        json={"verificacao_id": verificacao["verificacao_id"], "codigo": codigo},
    )

    assert client.get(f"/v1/clientes/{CLIENTE_ID_PADRAO}").json()["acesso_habilitado"] is True
