"""Contratos de autenticacao ja existentes."""


def test_me_sem_token_e_token_invalido(client):
    assert client.get("/v1/auth/me").status_code == 401
    assert client.get("/v1/auth/me", headers={"Authorization": "Bearer invalido"}).status_code == 401


def test_login_senha_errada(client, headers_auth):
    resposta = client.post(
        "/v1/auth/login",
        data={"username": "operacao@bulbe.com.br", "password": "incorreta"},
    )
    assert resposta.status_code == 401
