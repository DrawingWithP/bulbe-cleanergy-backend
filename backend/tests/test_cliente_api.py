"""
Testes de integração (HTTP) das rotas /v1/clientes (US-05, US-31 e US-34).
PUT e DELETE exigem token; GET e POST são públicos.
"""
from fastapi.testclient import TestClient

CLIENTE_ID_PADRAO = "8f1c2a6e-4b7d-4c1a-9f52-3d6a1b0c7e11"

NOVO_CLIENTE = {
    "nome": "Mariana Costa",
    "email": "mariana.costa@email.com",
    "cpf": "222.333.444-55",
    "telefone": "(31) 98765-4321",
    "endereco": {
        "cep": "30130-110",
        "logradouro": "Rua Sergipe",
        "numero": "800",
        "bairro": "Funcionários",
        "cidade": "Belo Horizonte",
        "uf": "MG",
    },
    "numero_instalacao": "5001234567",
}


def test_listar_clientes(client: TestClient):
    resposta = client.get("/v1/clientes")
    assert resposta.status_code == 200
    assert resposta.json()["total"] == 1
    assert resposta.json()["data"][0]["cidade"] == "Belo Horizonte"


def test_listar_clientes_limit_acima_de_100_retorna_422(client: TestClient):
    """O Query(le=100) do FastAPI barra o limite antes de chegar ao service."""
    assert client.get("/v1/clientes?limit=101").status_code == 422


def test_listar_clientes_status_invalido_retorna_422(client: TestClient):
    assert client.get("/v1/clientes?status=desconhecido").status_code == 422


def test_criar_cliente_retorna_201(client: TestClient):
    """US-31: Cadastro devolve a resposta enxuta, com distribuidora padrão CEMIG."""
    resposta = client.post("/v1/clientes", json=NOVO_CLIENTE)
    assert resposta.status_code == 201
    corpo = resposta.json()
    assert set(corpo) == {"id", "nome", "email", "status", "criado_em"}
    assert corpo["status"] == "em_ativacao"

    completo = client.get(f"/v1/clientes/{corpo['id']}").json()
    assert completo["distribuidora"] == "CEMIG"
    assert completo["cpf"] == "22233344455"


def test_criar_cliente_email_invalido_retorna_422(client: TestClient):
    resposta = client.post("/v1/clientes", json={**NOVO_CLIENTE, "email": "nao-e-email"})
    assert resposta.status_code == 422


def test_criar_cliente_cpf_invalido_retorna_400(client: TestClient):
    resposta = client.post("/v1/clientes", json={**NOVO_CLIENTE, "cpf": "123"})
    assert resposta.status_code == 400
    assert resposta.json()["error"]["code"] == "CPF_INVALIDO"


def test_criar_cliente_cpf_duplicado_retorna_409(client: TestClient):
    resposta = client.post("/v1/clientes", json={**NOVO_CLIENTE, "cpf": "12345678900"})
    assert resposta.status_code == 409
    assert resposta.json()["error"]["code"] == "CONFLITO_DADOS"


def test_buscar_cliente(client: TestClient):
    """US-05: Retorna os dados completos do cliente."""
    resposta = client.get(f"/v1/clientes/{CLIENTE_ID_PADRAO}")
    assert resposta.status_code == 200
    assert resposta.json()["nome"] == "Marcos Andrade"


def test_buscar_cliente_inexistente_retorna_404(client: TestClient):
    resposta = client.get("/v1/clientes/nao-existe")
    assert resposta.status_code == 404
    assert resposta.json()["error"]["code"] == "RECURSO_NAO_ENCONTRADO"


def test_atualizar_cliente_sem_token_retorna_401(client: TestClient):
    resposta = client.put(f"/v1/clientes/{CLIENTE_ID_PADRAO}", json={"telefone": "(31) 91111-2222"})
    assert resposta.status_code == 401


def test_atualizar_cliente_com_token(client: TestClient, headers_auth: dict):
    """US-34: Atualiza telefone e parte do endereço."""
    resposta = client.put(
        f"/v1/clientes/{CLIENTE_ID_PADRAO}",
        json={"telefone": "(31) 91111-2222", "endereco": {"numero": "1050"}},
        headers=headers_auth,
    )
    assert resposta.status_code == 200
    assert resposta.json()["telefone"] == "(31) 91111-2222"
    assert resposta.json()["endereco"]["numero"] == "1050"
    assert resposta.json()["endereco"]["logradouro"] == "Av. Afonso Pena"


def test_remover_cliente_sem_token_retorna_401(client: TestClient):
    assert client.delete(f"/v1/clientes/{CLIENTE_ID_PADRAO}").status_code == 401
    assert client.get(f"/v1/clientes/{CLIENTE_ID_PADRAO}").status_code == 200


def test_remover_cliente_com_token_retorna_204(client: TestClient, headers_auth: dict):
    assert client.delete(f"/v1/clientes/{CLIENTE_ID_PADRAO}", headers=headers_auth).status_code == 204
    assert client.get(f"/v1/clientes/{CLIENTE_ID_PADRAO}").status_code == 404
