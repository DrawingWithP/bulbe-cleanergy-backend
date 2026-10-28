"""
Testes de integração (HTTP) das rotas de Cupons (US-03, US-22 e US-23).
"""
from fastapi.testclient import TestClient

CLIENTE_ID_PADRAO = "8f1c2a6e-4b7d-4c1a-9f52-3d6a1b0c7e11"
CUPOM_ID_PADRAO = "f6b1d803-2e94-4a57-83cd-9b0e5a7c1d22"


def test_listar_cupons_do_cliente(client: TestClient):
    """US-03: Lista os cupons da carteira do cliente."""
    resposta = client.get(f"/v1/clientes/{CLIENTE_ID_PADRAO}/cupons")
    assert resposta.status_code == 200
    assert resposta.json()["total"] == 1
    assert resposta.json()["data"][0]["codigo"] == "BULBE15"


def test_listar_cupons_com_filtro_de_situacao(client: TestClient):
    resposta = client.get(f"/v1/clientes/{CLIENTE_ID_PADRAO}/cupons?situacao=usado")
    assert resposta.json()["total"] == 0


def test_listar_cupons_cliente_inexistente_retorna_404(client: TestClient):
    assert client.get("/v1/clientes/nao-existe/cupons").status_code == 404


def test_buscar_cupom(client: TestClient):
    """US-22: Retorna o cupom com o resumo do parceiro."""
    resposta = client.get(f"/v1/cupons/{CUPOM_ID_PADRAO}")
    assert resposta.status_code == 200
    assert resposta.json()["parceiro"]["nome"] == "Drogaria Araújo"


def test_marcar_cupom_como_usado(client: TestClient):
    """US-23: PATCH muda a situação para 'usado' e preenche usado_em."""
    resposta = client.patch(f"/v1/cupons/{CUPOM_ID_PADRAO}", json={"situacao": "usado"})
    assert resposta.status_code == 200
    assert resposta.json()["situacao"] == "usado"
    assert resposta.json()["usado_em"] is not None


def test_patch_situacao_nao_permitida_retorna_400(client: TestClient):
    resposta = client.patch(f"/v1/cupons/{CUPOM_ID_PADRAO}", json={"situacao": "expirado"})
    assert resposta.status_code == 400
    assert resposta.json()["error"]["code"] == "SITUACAO_INVALIDA"


def test_patch_situacao_fora_do_enum_retorna_422(client: TestClient):
    resposta = client.patch(f"/v1/cupons/{CUPOM_ID_PADRAO}", json={"situacao": "qualquer"})
    assert resposta.status_code == 422


def test_descartar_cupom_retorna_204(client: TestClient):
    assert client.delete(f"/v1/cupons/{CUPOM_ID_PADRAO}").status_code == 204
    assert client.get(f"/v1/cupons/{CUPOM_ID_PADRAO}").status_code == 404
