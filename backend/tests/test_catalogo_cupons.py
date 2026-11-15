"""
Catalogo de cupons e sorteio do cupom da semana (cartas normais).
"""

import random

from app.db.seed import CATALOGO_CUPONS, ID_ARAUJO, ID_CARTA_MARCOS, ID_MARCOS, popular
from app.repositories.carta_repository import SqlCartaRepository
from app.db.database import SessionLocal
from app.services.carta_service import CartaService


NOVO_MODELO = {
    "parceiro_id": ID_ARAUJO,
    "titulo": "20% em vitaminas na Araújo",
    "descricao": "Desconto em vitaminas e suplementos nas lojas Araújo.",
    "tag": "PARCERIA DROGARIA ARAÚJO",
    "prefixo_codigo": "ARAUJO20",
    "validade_dias": 10,
    "peso": 5,
}


def _popular(session_factory):
    with session_factory() as session:
        popular(session)


def _avancar(client, headers, dias):
    assert client.post("/v1/demonstracao/relogio/avancar", json={"dias": dias}, headers=headers).status_code == 200


# ---------------------------------------------------------------- CRUD


def test_catalogo_exige_token(client):
    assert client.get("/v1/catalogo-cupons").status_code == 401
    assert client.post("/v1/catalogo-cupons", json=NOVO_MODELO).status_code == 401


def test_seed_cadastra_o_catalogo(client, session_factory, headers_auth):
    _popular(session_factory)
    catalogo = client.get("/v1/catalogo-cupons", headers=headers_auth).json()
    assert len(catalogo) == len(CATALOGO_CUPONS)
    assert {m["parceiro_nome"] for m in catalogo} == {"Drogaria Araújo", "Banco Inter", "Livelo"}


def test_cadastrar_alterar_e_remover(client, session_factory, headers_auth):
    _popular(session_factory)
    criado = client.post("/v1/catalogo-cupons", json=NOVO_MODELO, headers=headers_auth)
    assert criado.status_code == 201, criado.text
    modelo = criado.json()
    assert modelo["parceiro_nome"] == "Drogaria Araújo"
    assert modelo["ativo"] is True

    alterado = client.patch(f"/v1/catalogo-cupons/{modelo['id']}", json={"ativo": False, "peso": 1},
                            headers=headers_auth).json()
    assert alterado["ativo"] is False
    assert alterado["titulo"] == NOVO_MODELO["titulo"]

    ativos = client.get("/v1/catalogo-cupons?apenas_ativos=true", headers=headers_auth).json()
    assert modelo["id"] not in [m["id"] for m in ativos]

    assert client.delete(f"/v1/catalogo-cupons/{modelo['id']}", headers=headers_auth).status_code == 204
    assert client.get(f"/v1/catalogo-cupons/{modelo['id']}", headers=headers_auth).status_code == 404


def test_validacoes_do_catalogo(client, session_factory, headers_auth):
    _popular(session_factory)
    sem_parceiro = client.post("/v1/catalogo-cupons", json={**NOVO_MODELO, "parceiro_id": "nao-existe"},
                               headers=headers_auth)
    assert sem_parceiro.status_code == 422
    assert sem_parceiro.json()["error"]["code"] == "PARCEIRO_NAO_ENCONTRADO"
    for campo, valor in (("prefixo_codigo", "minusculo"), ("peso", 11), ("validade_dias", 0)):
        assert client.post("/v1/catalogo-cupons", json={**NOVO_MODELO, campo: valor},
                           headers=headers_auth).status_code == 422


# ---------------------------------------------------------------- sorteio


def test_carta_normal_sorteia_um_cupom_do_catalogo(client, session_factory):
    _popular(session_factory)
    cupom = client.post(f"/v1/cartas/{ID_CARTA_MARCOS}/abertura").json()["cupom"]
    titulos = {modelo[3] for modelo in CATALOGO_CUPONS}
    prefixos = tuple(modelo[5] for modelo in CATALOGO_CUPONS)
    assert cupom["titulo"] in titulos
    assert cupom["codigo"].startswith(prefixos)


def test_mesmo_cliente_nao_repete_o_cupom_da_semana_anterior(client, session_factory, headers_auth):
    _popular(session_factory)
    carta_id = ID_CARTA_MARCOS
    modelos = []
    for _ in range(2):
        abertura = client.post(f"/v1/cartas/{carta_id}/abertura").json()
        modelos.append(abertura["cupom"]["modelo_id"])
        _avancar(client, headers_auth, 7)
        carta_id = client.get(f"/v1/clientes/{ID_MARCOS}/clube").json()["proxima_carta"]["carta_id"]
    assert modelos[0] and modelos[1]
    assert modelos[0] != modelos[1]


def test_sorteio_varia_entre_clientes(session_factory):
    """Com geradores diferentes, clientes recebem cupons diferentes (nao e sempre o mesmo)."""
    _popular(session_factory)
    from app.services.cupom_catalogo_service import cupom_catalogo_service

    sorteados = {
        cupom_catalogo_service.sortear(sorteio=random.Random(semente)).id
        for semente in range(30)
    }
    assert len(sorteados) > 1


def test_catalogo_vazio_usa_o_cupom_reserva(client, session_factory, headers_auth):
    _popular(session_factory)
    for modelo in client.get("/v1/catalogo-cupons", headers=headers_auth).json():
        client.patch(f"/v1/catalogo-cupons/{modelo['id']}", json={"ativo": False}, headers=headers_auth)
    cupom = client.post(f"/v1/cartas/{ID_CARTA_MARCOS}/abertura").json()["cupom"]
    assert cupom["titulo"] == "500 pontos Livelo"
    assert cupom["modelo_id"] is None


def test_sorteio_reproduzivel_com_semente(session_factory):
    _popular(session_factory)
    servico_a = CartaService(SqlCartaRepository(SessionLocal), sorteio=random.Random(7))
    resultado = servico_a.abrir_carta(ID_CARTA_MARCOS)
    assert resultado.cupom.modelo_id in {modelo[0] for modelo in CATALOGO_CUPONS}
