"""
Testes de integracao da API: HTTP -> Controller -> Service -> Repositorio SQL -> bulbe_test.db.
"""
from fastapi.testclient import TestClient

from app.db.seed import ID_CARTA_MARCOS, ID_MARCOS, popular
from app.main import app
from app.repositories.primeiro_acesso_repository import primeiro_acesso_repository


def test_usina_criada_continua_la_depois_de_reiniciar(client, headers_auth, usina_valida):
    resposta = client.post("/v1/usinas", json=usina_valida, headers=headers_auth)
    assert resposta.status_code == 201

    # Um TestClient novo e como subir a API de novo: o dado tem que vir do banco.
    lista = TestClient(app).get("/v1/usinas").json()

    assert len(lista) == 1
    assert lista[0]["nome"] == "Usina Solar Uberlandia"
    assert lista[0]["id"] == resposta.json()["id"]


def test_criar_usina_sem_token_retorna_401(client, usina_valida):
    resposta = client.post("/v1/usinas", json=usina_valida)

    assert resposta.status_code == 401
    assert resposta.json()["error"]["code"] == "TOKEN_INVALIDO"


def test_remover_usina_com_token(client, headers_auth, usina_valida):
    usina_id = client.post("/v1/usinas", json=usina_valida, headers=headers_auth).json()["id"]

    assert client.delete(f"/v1/usinas/{usina_id}", headers=headers_auth).status_code == 204
    assert client.get(f"/v1/usinas/{usina_id}").status_code == 404


def test_registrar_e_logar_com_usuario_do_banco(client):
    dados = {"nome": "Operadora Bulbe", "email": "Operacao@Bulbe.com.br", "senha": "solar12345"}
    assert client.post("/v1/auth/registrar", json=dados).status_code == 201
    assert client.post("/v1/auth/registrar", json=dados).status_code == 409

    token = client.post(
        "/v1/auth/login", data={"username": "operacao@bulbe.com.br", "password": "solar12345"}
    ).json()["access_token"]
    eu = client.get("/v1/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert eu.status_code == 200
    assert eu.json()["email"] == "operacao@bulbe.com.br"


def test_cliente_e_jornada_de_ativacao(client, cliente_valido):
    criado = client.post("/v1/clientes", json=cliente_valido)
    assert criado.status_code == 201
    cliente_id = criado.json()["id"]

    assert client.post("/v1/clientes", json=cliente_valido).status_code == 409
    assert client.get(f"/v1/clientes/{cliente_id}").json()["cpf"] == "16899535009"
    assert client.get(f"/v1/clientes/{cliente_id}/ativacao").json()["etapa_atual"] == 1

    patch = client.patch(f"/v1/clientes/{cliente_id}/ativacao", json={"etapa_atual": 3})

    assert patch.status_code == 200
    assert patch.json()["percentual_concluido"] == 45
    assert client.get(f"/v1/clientes/{cliente_id}/ativacao").json()["etapa_atual"] == 3


def test_primeiro_acesso_habilita_o_cliente_cadastrado(client, cliente_valido):
    cliente_id = client.post("/v1/clientes", json=cliente_valido).json()["id"]

    verificacao = client.post("/v1/primeiro-acesso/verificacoes", json={"cpf": "16899535009"})
    assert verificacao.status_code == 202
    verificacao_id = verificacao.json()["verificacao_id"]
    codigo = primeiro_acesso_repository.buscar_verificacao_por_id(verificacao_id).codigo

    confirmacao = client.post(
        "/v1/primeiro-acesso/confirmacoes",
        json={"verificacao_id": verificacao_id, "codigo": codigo},
    )

    assert confirmacao.status_code == 201
    assert client.get(f"/v1/clientes/{cliente_id}").json()["acesso_habilitado"] is True


def test_abrir_carta_gera_cupom_e_avanca_ofensiva(client, session_factory):
    with session_factory() as session:
        popular(session)

    abertura = client.post(f"/v1/cartas/{ID_CARTA_MARCOS}/abertura")
    assert abertura.status_code == 201
    assert abertura.json()["semanas_sequencia"] == 4

    clube = client.get(f"/v1/clientes/{ID_MARCOS}/clube").json()
    cupons = client.get(f"/v1/clientes/{ID_MARCOS}/cupons").json()
    reabertura = client.post(f"/v1/cartas/{ID_CARTA_MARCOS}/abertura").json()

    assert clube["semanas_sequencia"] == 4
    assert clube["carta_disponivel"] is False
    assert cupons["total"] == 2
    assert reabertura["cupom"]["id"] == abertura.json()["cupom"]["id"]


def test_remover_cliente_remove_os_cupons_dele(client, session_factory, headers_auth):
    with session_factory() as session:
        popular(session)
    cupom_id = client.get(f"/v1/clientes/{ID_MARCOS}/cupons").json()["data"][0]["id"]

    assert client.delete(f"/v1/clientes/{ID_MARCOS}", headers=headers_auth).status_code == 204
    assert client.get(f"/v1/cupons/{cupom_id}").status_code == 404


def test_adesao_e_indicacao_persistem(client):
    adesao = {
        "nome": "Joao da Silva", "email": "joao@email.com", "cpf": "14444444444",
        "telefone": "31999999999", "cep": "30575160", "logradouro": "Rua Oliveira",
        "numero": 213, "bairro": "Buritis", "cidade": "Belo Horizonte", "uf": "MG",
        "distribuidora": "CEMIG", "numero_instalacao": "3242412", "valor_conta_atual": 399.0,
    }
    adesao_id = client.post("/v1/adesoes", json=adesao).json()["id"]
    assert client.post("/v1/adesoes", json=adesao).status_code == 409

    indicacao = client.post(
        "/v1/indicacoes", json={"cliente_id": 1, "nome": "Maria Souza", "contato": "maria@email.com"}
    )
    assert indicacao.status_code == 201
    assert client.post(
        "/v1/indicacoes", json={"cliente_id": 1, "nome": "Maria", "contato": "MARIA@email.com"}
    ).status_code == 409

    novo_client = TestClient(app)
    assert novo_client.get(f"/v1/adesoes/{adesao_id}").json()["cpf"] == "14444444444"
    assert len(novo_client.get("/v1/clientes/1/indicacoes").json()) == 1


def test_seed_e_idempotente(session_factory):
    with session_factory() as session:
        primeira = popular(session)
    with session_factory() as session:
        segunda = popular(session)

    assert primeira > 0
    assert segunda == 0
