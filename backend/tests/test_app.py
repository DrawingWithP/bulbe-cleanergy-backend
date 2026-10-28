"""
Testes gerais da aplicação: rota raiz, documentação e rotas inexistentes.
"""
from fastapi.testclient import TestClient


def test_raiz_responde_que_a_api_esta_no_ar(client: TestClient):
    resposta = client.get("/")
    assert resposta.status_code == 200
    assert "API no ar" in resposta.json()["mensagem"]


def test_swagger_e_openapi_estao_disponiveis(client: TestClient):
    assert client.get("/docs").status_code == 200
    esquema = client.get("/openapi.json").json()
    assert esquema["info"]["title"] == "Bulbe Energia, API"


def test_todos_os_modulos_estao_registrados(client: TestClient):
    """Garante que nenhum router foi esquecido no main.py."""
    rotas = client.get("/openapi.json").json()["paths"]
    prefixos = [
        "/v1/auth/login",
        "/v1/usinas",
        "/v1/adesoes",
        "/v1/dicas",
        "/v1/simulacaos",
        "/v1/indicacoes",
        "/v1/primeiro-acesso/verificacoes",
        "/v1/clientes",
        "/v1/clientes/{cliente_id}/ativacao",
        "/v1/parceiros",
        "/v1/cupons/{cupom_id}",
        "/v1/cartas/{carta_id}",
    ]
    for prefixo in prefixos:
        assert prefixo in rotas, f"rota {prefixo} não registrada"


def test_rota_inexistente_retorna_404(client: TestClient):
    assert client.get("/v1/rota-que-nao-existe").status_code == 404
