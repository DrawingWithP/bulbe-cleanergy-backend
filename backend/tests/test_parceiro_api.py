"""
Testes de integração (HTTP) das rotas /v1/parceiros (US-02, US-24, US-25, US-26 e US-33).
"""
from fastapi.testclient import TestClient

PARCEIRO_ID_PADRAO = "1d2c3b4a-5e6f-4071-8293-a4b5c6d7e8f9"


def test_listar_parceiros(client: TestClient):
    """US-02 / US-33: Lista os parceiros do Clube Bulbe."""
    resposta = client.get("/v1/parceiros")
    assert resposta.status_code == 200
    assert resposta.json()["total"] == 2


def test_listar_parceiros_com_filtros(client: TestClient):
    resposta = client.get("/v1/parceiros?categoria=farmácia&ativo=true")
    assert [p["nome"] for p in resposta.json()["data"]] == ["Drogaria Araújo"]


def test_listar_parceiros_paginado(client: TestClient):
    resposta = client.get("/v1/parceiros?page=2&limit=1")
    assert resposta.json()["page"] == 2
    assert len(resposta.json()["data"]) == 1


def test_criar_parceiro_retorna_201(client: TestClient):
    """US-24: Cadastra um novo parceiro."""
    resposta = client.post("/v1/parceiros", json={"nome": "Livelo", "categoria": "Programa de pontos"})
    assert resposta.status_code == 201
    assert resposta.json()["ativo"] is True


def test_criar_parceiro_duplicado_retorna_409(client: TestClient):
    resposta = client.post("/v1/parceiros", json={"nome": "Banco Inter", "categoria": "Banco"})
    assert resposta.status_code == 409
    assert resposta.json()["error"]["code"] == "CONFLITO_DADOS"


def test_criar_parceiro_sem_categoria_retorna_422(client: TestClient):
    assert client.post("/v1/parceiros", json={"nome": "Livelo"}).status_code == 422


def test_buscar_parceiro(client: TestClient):
    """US-25: Consulta um parceiro pelo id."""
    resposta = client.get(f"/v1/parceiros/{PARCEIRO_ID_PADRAO}")
    assert resposta.status_code == 200
    assert resposta.json()["categoria"] == "Farmácia"


def test_buscar_parceiro_inexistente_retorna_404(client: TestClient):
    assert client.get("/v1/parceiros/nao-existe").status_code == 404


def test_atualizar_parceiro(client: TestClient):
    resposta = client.put(f"/v1/parceiros/{PARCEIRO_ID_PADRAO}", json={"ativo": False})
    assert resposta.status_code == 200
    assert resposta.json()["ativo"] is False


def test_remover_parceiro_retorna_204(client: TestClient):
    """US-26: Remove o parceiro do Clube."""
    assert client.delete(f"/v1/parceiros/{PARCEIRO_ID_PADRAO}").status_code == 204
    assert client.get(f"/v1/parceiros/{PARCEIRO_ID_PADRAO}").status_code == 404
