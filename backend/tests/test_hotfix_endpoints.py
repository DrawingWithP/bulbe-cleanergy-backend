"""Contratos HTTP das operacoes registradas, com banco isolado."""

import re

import pytest

from app.db.seed import (
    CPF_MARCOS, EMAIL_ADMIN, SENHA_ADMIN, ID_ARAUJO,
    ID_CARTA_MARCOS, ID_CUPOM_MARCOS, ID_MARCOS, popular,
)
from app.main import app
from app.repositories.primeiro_acesso_repository import primeiro_acesso_repository


# Inventario explicito: uma rota nova ou removida exige rever a cobertura.
CASOS = [
    ("POST", "/v1/auth/registrar", 201),
    ("POST", "/v1/auth/login", 200),
    ("GET", "/v1/auth/me", 200),
    ("GET", "/v1/usinas", 200),
    ("POST", "/v1/usinas", 201),
    ("GET", "/v1/usinas/{usina_id}", 200),
    ("PUT", "/v1/usinas/{usina_id}", 200),
    ("DELETE", "/v1/usinas/{usina_id}", 204),
    ("GET", "/v1/adesoes", 200),
    ("POST", "/v1/adesoes", 201),
    ("GET", "/v1/adesoes/{adesao_id}", 200),
    ("PUT", "/v1/adesoes/{adesao_id}", 200),
    ("DELETE", "/v1/adesoes/{adesao_id}", 204),
    ("GET", "/v1/dicas", 200),
    ("POST", "/v1/dicas", 201),
    ("GET", "/v1/dicas/{dica_id}", 200),
    ("PUT", "/v1/dicas/{dica_id}", 200),
    ("DELETE", "/v1/dicas/{dica_id}", 204),
    ("POST", "/v1/simulacoes", 201),
    ("POST", "/v1/indicacoes", 201),
    ("GET", "/v1/indicacoes/{indicacao_id}", 200),
    ("DELETE", "/v1/indicacoes/{indicacao_id}", 204),
    ("GET", "/v1/clientes/{cliente_id}/indicacoes", 200),
    ("POST", "/v1/primeiro-acesso/verificacoes", 202),
    ("POST", "/v1/primeiro-acesso/confirmacoes", 201),
    ("GET", "/v1/clientes", 200),
    ("POST", "/v1/clientes", 201),
    ("GET", "/v1/clientes/{cliente_id}", 200),
    ("PUT", "/v1/clientes/{cliente_id}", 200),
    ("DELETE", "/v1/clientes/{cliente_id}", 204),
    ("GET", "/v1/clientes/{cliente_id}/ativacao", 200),
    ("PATCH", "/v1/clientes/{cliente_id}/ativacao", 200),
    ("GET", "/v1/clientes/{cliente_id}/ativacao/etapas", 200),
    ("GET", "/v1/parceiros", 200),
    ("POST", "/v1/parceiros", 201),
    ("GET", "/v1/parceiros/{parceiro_id}", 200),
    ("PUT", "/v1/parceiros/{parceiro_id}", 200),
    ("DELETE", "/v1/parceiros/{parceiro_id}", 204),
    ("GET", "/v1/clientes/{cliente_id}/cupons", 200),
    ("GET", "/v1/cupons/{cupom_id}", 200),
    ("PATCH", "/v1/cupons/{cupom_id}", 200),
    ("DELETE", "/v1/cupons/{cupom_id}", 204),
    ("GET", "/v1/clientes/{cliente_id}/clube", 200),
    ("GET", "/v1/clientes/{cliente_id}/cartas", 200),
    ("GET", "/v1/cartas/{carta_id}", 200),
    ("POST", "/v1/cartas/{carta_id}/abertura", 201),
    ("GET", "/", 200),
]
ESQUEMA = app.openapi()
ROTAS = {(m.upper(), p): op for p, ops in ESQUEMA["paths"].items()
         for m, op in ops.items() if m in {"get", "post", "put", "patch", "delete"}}
PROTEGIDAS = {
    ("GET", "/v1/auth/me"),
    ("POST", "/v1/usinas"),
    ("PUT", "/v1/usinas/{usina_id}"),
    ("DELETE", "/v1/usinas/{usina_id}"),
    ("PUT", "/v1/adesoes/{adesao_id}"),
    ("DELETE", "/v1/adesoes/{adesao_id}"),
    ("POST", "/v1/dicas"),
    ("PUT", "/v1/dicas/{dica_id}"),
    ("DELETE", "/v1/dicas/{dica_id}"),
    ("DELETE", "/v1/indicacoes/{indicacao_id}"),
    ("PUT", "/v1/clientes/{cliente_id}"),
    ("DELETE", "/v1/clientes/{cliente_id}"),
}


def test_inventario_e_autenticacao_dos_contratos():
    assert set(ROTAS) == {(m, p) for m, p, _ in CASOS}
    assert len(CASOS) == len(ROTAS) == 47
    assert {rota for rota, op in ROTAS.items() if op.get("security")} == PROTEGIDAS


def _url(caminho):
    ids = {"usina_id": 1, "adesao_id": 1, "dica_id": 1, "indicacao_id": 1,
           "cliente_id": ID_MARCOS, "parceiro_id": ID_ARAUJO,
           "cupom_id": ID_CUPOM_MARCOS, "carta_id": ID_CARTA_MARCOS}
    # Indicacoes ja usavam um ID inteiro, independentemente dos UUIDs de clientes.
    if caminho.endswith("/indicacoes"):
        ids["cliente_id"] = 1
    return caminho.format(**ids)


@pytest.fixture
def contratos(client, session_factory, adesao_valida, cliente_valido, usina_valida):
    with session_factory() as session:
        popular(session)
    login = client.post("/v1/auth/login", data={"username": EMAIL_ADMIN, "password": SENHA_ADMIN})
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    indicacao = {"cliente_id": 1, "nome": "Maria Silva", "contato": "maria@example.com"}
    assert client.post("/v1/indicacoes", json=indicacao).status_code == 201
    verificacao = client.post("/v1/primeiro-acesso/verificacoes", json={"cpf": CPF_MARCOS})
    assert verificacao.status_code == 202
    vid = verificacao.json()["verificacao_id"]
    return headers, {
        "/v1/auth/registrar": {"nome": "Novo Usuario", "email": "novo@example.com", "senha": "solar12345"},
        "/v1/usinas": usina_valida,
        "/v1/usinas/{usina_id}": {"nome": "Usina Atualizada"},
        "/v1/adesoes": {**adesao_valida, "cpf": "12345678909"},
        "/v1/adesoes/{adesao_id}": {"nome": "Adesao Atualizada"},
        "/v1/dicas": {"titulo": "Economize energia", "descricao": "Apague as luzes.", "economia": 20, "imagem_svg": "<svg/>"},
        "/v1/dicas/{dica_id}": {"titulo": "Dica Atualizada"},
        "/v1/simulacoes": {"valor_atual": 400, "valor_proposto": 320, "periodo_meses": 12, "indicacoes": 2},
        "/v1/indicacoes": {**indicacao, "contato": "outra@example.com"},
        "/v1/primeiro-acesso/verificacoes": {"cpf": CPF_MARCOS},
        "/v1/primeiro-acesso/confirmacoes": {"verificacao_id": vid, "codigo": primeiro_acesso_repository.buscar_verificacao_por_id(vid).codigo},
        "/v1/clientes": cliente_valido,
        "/v1/clientes/{cliente_id}": {"nome": "Cliente Atualizado"},
        "/v1/clientes/{cliente_id}/ativacao": {"etapa_atual": 3},
        "/v1/parceiros": {"nome": "Novo Parceiro", "categoria": "Energia"},
        "/v1/parceiros/{parceiro_id}": {"nome": "Parceiro Atualizado"},
        "/v1/cupons/{cupom_id}": {"situacao": "salvo"},
    }


@pytest.mark.parametrize("metodo,caminho,status", CASOS, ids=[f"{m} {p}" for m, p, _ in CASOS])
def test_contrato_com_entrada_valida(client, contratos, metodo, caminho, status):
    headers, corpos = contratos
    argumentos = {"headers": headers} if (metodo, caminho) in PROTEGIDAS else {}
    if caminho == "/v1/auth/login":
        argumentos["data"] = {"username": EMAIL_ADMIN, "password": SENHA_ADMIN}
    elif metodo in {"POST", "PUT", "PATCH"} and caminho in corpos:
        argumentos["json"] = corpos[caminho]
    resposta = client.request(metodo, _url(caminho), **argumentos)
    assert resposta.status_code == status, resposta.text
    assert str(status) in ROTAS[metodo, caminho]["responses"]
    if status == 204:
        assert resposta.content == b""
    else:
        assert isinstance(resposta.json(), (dict, list))


@pytest.mark.parametrize("metodo,caminho", sorted(PROTEGIDAS))
@pytest.mark.parametrize("token", [None, "invalido"])
def test_autenticacao_original(client, metodo, caminho, token):
    headers = {} if token is None else {"Authorization": f"Bearer {token}"}
    resposta = client.request(metodo, re.sub(r"\{[^{}]+\}", "999999", caminho), headers=headers)
    assert resposta.status_code == 401
    assert resposta.headers["www-authenticate"] == "Bearer"
    assert resposta.json()["error"]["code"] == "TOKEN_INVALIDO"


@pytest.mark.parametrize("metodo,caminho", [k for k, op in ROTAS.items() if "requestBody" in op])
def test_corpo_ausente_retorna_422(client, headers_auth, metodo, caminho):
    resposta = client.request(metodo, re.sub(r"\{[^{}]+\}", "999999", caminho), headers=headers_auth)
    assert resposta.status_code == 422
    assert isinstance(resposta.json()["detail"], list)
