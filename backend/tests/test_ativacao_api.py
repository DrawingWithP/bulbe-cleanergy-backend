"""
Testes de integração (HTTP) das rotas de Ativação CEMIG (US-11 e US-12).
"""
from fastapi.testclient import TestClient

CLIENTE_ID_PADRAO = "8f1c2a6e-4b7d-4c1a-9f52-3d6a1b0c7e11"
URL = f"/v1/clientes/{CLIENTE_ID_PADRAO}/ativacao"


def test_consultar_resumo_da_ativacao(client: TestClient):
    """US-11: Resumo com etapa atual, percentual e prazo."""
    resposta = client.get(URL)
    assert resposta.status_code == 200
    assert resposta.json()["etapa_atual"] == 2
    assert resposta.json()["prazo_ativacao_dias"] == 90


def test_listar_etapas(client: TestClient):
    resposta = client.get(f"{URL}/etapas")
    assert resposta.status_code == 200
    assert [e["situacao"] for e in resposta.json()["data"]] == [
        "concluida", "atual", "pendente", "pendente", "pendente",
    ]


def test_avancar_etapa(client: TestClient):
    """US-12: PATCH avança a etapa e o GET seguinte já mostra a mudança."""
    resposta = client.patch(URL, json={"etapa_atual": 4, "observacao": "Em análise na CEMIG"})
    assert resposta.status_code == 200
    assert resposta.json()["percentual_concluido"] == 75
    assert client.get(URL).json()["etapa_atual"] == 4


def test_etapa_fora_do_intervalo_retorna_422(client: TestClient):
    assert client.patch(URL, json={"etapa_atual": 6}).status_code == 422


def test_cliente_inexistente_retorna_404(client: TestClient):
    resposta = client.get("/v1/clientes/nao-existe/ativacao")
    assert resposta.status_code == 404
    assert resposta.json()["error"]["code"] == "RECURSO_NAO_ENCONTRADO"
