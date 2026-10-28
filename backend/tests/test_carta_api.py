"""
Testes de integração (HTTP) das rotas do Clube Bulbe e Cartas (US-18 a US-21).
"""
from fastapi.testclient import TestClient

CLIENTE_ID_PADRAO = "8f1c2a6e-4b7d-4c1a-9f52-3d6a1b0c7e11"
CARTA_ID_PADRAO = "a7c4e2b9-5d31-4f80-9e6b-8c2a1d4f7b55"


def test_situacao_do_clube(client: TestClient):
    """US-18: Mostra a ofensiva e se há carta disponível."""
    resposta = client.get(f"/v1/clientes/{CLIENTE_ID_PADRAO}/clube")
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["semanas_sequencia"] == 3
    assert corpo["carta_disponivel"] is True
    assert corpo["proxima_carta"]["carta_id"] == CARTA_ID_PADRAO


def test_situacao_do_clube_cliente_inexistente_retorna_404(client: TestClient):
    resposta = client.get("/v1/clientes/nao-existe/clube")
    assert resposta.status_code == 404
    assert resposta.json()["error"]["code"] == "RECURSO_NAO_ENCONTRADO"


def test_listar_cartas_do_cliente(client: TestClient):
    """US-19: Histórico de cartas, com filtro opcional de situação."""
    assert client.get(f"/v1/clientes/{CLIENTE_ID_PADRAO}/cartas").json()["total"] == 1
    filtrado = client.get(f"/v1/clientes/{CLIENTE_ID_PADRAO}/cartas?situacao=aberta")
    assert filtrado.json()["total"] == 0


def test_buscar_carta(client: TestClient):
    """US-20: Consulta uma carta pelo id."""
    resposta = client.get(f"/v1/cartas/{CARTA_ID_PADRAO}")
    assert resposta.status_code == 200
    assert resposta.json()["situacao"] == "disponivel"


def test_abrir_carta_retorna_201_com_cupom(client: TestClient):
    """US-21: Abrir a carta gera um cupom que já pode ser consultado na rota de cupons."""
    resposta = client.post(f"/v1/cartas/{CARTA_ID_PADRAO}/abertura")
    assert resposta.status_code == 201
    cupom = resposta.json()["cupom"]

    assert client.get(f"/v1/cupons/{cupom['id']}").status_code == 200
    assert client.get(f"/v1/clientes/{CLIENTE_ID_PADRAO}/cupons").json()["total"] == 2


def test_abrir_carta_duas_vezes_devolve_o_mesmo_cupom(client: TestClient):
    """US-21: A abertura é idempotente."""
    primeira = client.post(f"/v1/cartas/{CARTA_ID_PADRAO}/abertura").json()
    segunda = client.post(f"/v1/cartas/{CARTA_ID_PADRAO}/abertura").json()
    assert primeira["cupom"]["id"] == segunda["cupom"]["id"]
    assert segunda["semanas_sequencia"] == 4


def test_abrir_carta_inexistente_retorna_404(client: TestClient):
    assert client.post("/v1/cartas/nao-existe/abertura").status_code == 404
