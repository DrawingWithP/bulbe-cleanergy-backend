"""Regressoes de dicas e consulta de parceiros."""


def test_criar_dica_exige_token(client):
    assert client.post("/v1/dicas", json={}).status_code == 401


def test_criar_e_listar_dica(client, headers_auth):
    dados = {
        "titulo": "Apague a luz",
        "descricao": "Desligue lampadas quando nao houver pessoas no ambiente.",
        "economia": 20.0,
        "imagem_svg": "<svg></svg>",
    }
    criado = client.post("/v1/dicas", json=dados, headers=headers_auth)
    assert criado.status_code == 201
    consulta = client.get(f"/v1/dicas/{criado.json()['id']}")
    assert consulta.status_code == 200
    assert consulta.json()["titulo"] == dados["titulo"]
    assert client.get("/v1/dicas").json()[0]["id"] == criado.json()["id"]


def test_atualizar_dica_ausente_retorna_404(client, headers_auth):
    resposta = client.put("/v1/dicas/999999", json={"titulo": "Nao encontrada"}, headers=headers_auth)
    assert resposta.status_code == 404


def test_listagem_parceiros_responde_sem_token(client):
    assert client.get("/v1/parceiros").status_code == 200


def test_mutacoes_parceiros_preservam_acesso_publico_original(client):
    dados = {"nome": "Parceiro Teste", "categoria": "Energia"}
    criado = client.post("/v1/parceiros", json=dados)
    assert criado.status_code == 201
    caminho = f"/v1/parceiros/{criado.json()['id']}"
    atualizado = client.put(caminho, json={"nome": "Parceiro Atualizado"})
    assert atualizado.status_code == 200
    assert client.get(caminho).json()["nome"] == "Parceiro Atualizado"
    assert client.delete(caminho).status_code == 204
    assert client.get(caminho).status_code == 404
