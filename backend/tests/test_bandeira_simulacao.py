"""
RF-03: bandeiras tarifarias e calculo da economia no simulador.
"""

import pytest

from app.db.seed import ID_MARCOS, popular
from app.domain.bandeira import (
    ADICIONAL_POR_KWH,
    TARIFA_MEDIA_KWH,
    BandeiraTarifaria,
    mes_referencia_atual,
)
from app.repositories.bandeira_repository import InMemoryBandeiraRepository
from app.services.bandeira_service import BandeiraService, ErroDeNegocio
from app.services.simulacao_service import calcular_economia


SIMULACAO = {
    "valor_atual": 200,
    "valor_proposto": 170,
    "periodo_meses": 3,
    "indicacoes": 1,
}


# ---------------------------------------------------------------- calculo


def test_bandeira_verde_reproduz_o_calculo_do_app():
    # Conta R$ 200, 15% de desconto, 3 meses, 1 indicacao (exemplo do INTEGRATION.md).
    mensal, total = calcular_economia(200, 170, 3, 1, BandeiraTarifaria.verde)
    assert mensal == 30.0
    assert total == 140.0


def test_bandeira_vermelha_aumenta_a_economia():
    verde, _ = calcular_economia(200, 170, 12, 0, BandeiraTarifaria.verde)
    amarela, _ = calcular_economia(200, 170, 12, 0, BandeiraTarifaria.amarela)
    vermelha, _ = calcular_economia(200, 170, 12, 0, BandeiraTarifaria.vermelha_2)
    assert verde < amarela < vermelha

    consumo = 200 / TARIFA_MEDIA_KWH
    esperado = round((200 + consumo * ADICIONAL_POR_KWH[BandeiraTarifaria.vermelha_2]) * 0.15, 2)
    assert vermelha == esperado


def test_valor_proposto_maior_que_o_atual_nao_gera_economia_negativa():
    mensal, total = calcular_economia(100, 150, 12, 0, BandeiraTarifaria.verde)
    assert mensal == 0.0
    assert total == 0.0


# ---------------------------------------------------------------- servico


def test_servico_usa_verde_quando_o_mes_nao_foi_cadastrado():
    servico = BandeiraService(InMemoryBandeiraRepository())
    atual = servico.obter()
    assert atual.bandeira == BandeiraTarifaria.verde
    assert atual.definida is False
    assert atual.mes_referencia == mes_referencia_atual()


def test_servico_rejeita_mes_invalido():
    servico = BandeiraService(InMemoryBandeiraRepository())
    for mes in ("2026-13", "2026-1", "novembro"):
        with pytest.raises(ErroDeNegocio) as erro:
            servico.definir(mes, BandeiraTarifaria.amarela)
        assert erro.value.status == 422


# ---------------------------------------------------------------- API


def test_definir_e_consultar_bandeira(client, headers_auth):
    mes = mes_referencia_atual()

    assert client.get("/v1/bandeiras/atual").json()["definida"] is False

    resposta = client.put(f"/v1/bandeiras/{mes}", json={"bandeira": "vermelha_1"}, headers=headers_auth)
    assert resposta.status_code == 200
    assert resposta.json()["adicional_por_kwh"] == ADICIONAL_POR_KWH[BandeiraTarifaria.vermelha_1]

    atual = client.get("/v1/bandeiras/atual").json()
    assert atual["bandeira"] == "vermelha_1"
    assert atual["definida"] is True
    assert [b["mes_referencia"] for b in client.get("/v1/bandeiras").json()] == [mes]


def test_definir_bandeira_invalida_retorna_422(client, headers_auth):
    assert client.put("/v1/bandeiras/2026-11", json={"bandeira": "roxa"}, headers=headers_auth).status_code == 422
    resposta = client.put("/v1/bandeiras/2026-99", json={"bandeira": "verde"}, headers=headers_auth)
    assert resposta.status_code == 422
    assert resposta.json()["error"]["code"] == "MES_REFERENCIA_INVALIDO"


def test_simulacao_usa_a_bandeira_vigente(client, headers_auth):
    sem_bandeira = client.post("/v1/simulacoes", json=SIMULACAO).json()
    assert sem_bandeira["bandeira"] == "verde"
    assert sem_bandeira["economia_mensal"] == 30.0
    assert sem_bandeira["economia_total"] == 140.0

    client.put(f"/v1/bandeiras/{mes_referencia_atual()}", json={"bandeira": "amarela"}, headers=headers_auth)
    com_bandeira = client.post("/v1/simulacoes", json=SIMULACAO).json()
    assert com_bandeira["bandeira"] == "amarela"
    assert com_bandeira["economia_mensal"] > 30.0


def test_simulacao_aceita_bandeira_explicita(client):
    resposta = client.post("/v1/simulacoes", json={**SIMULACAO, "bandeira": "vermelha_2"})
    assert resposta.status_code == 201
    assert resposta.json()["bandeira"] == "vermelha_2"


def test_simulacao_logada_guarda_o_cliente(client, session_factory):
    with session_factory() as session:
        popular(session)
    resposta = client.post("/v1/simulacoes", json={**SIMULACAO, "cliente_id": ID_MARCOS})
    assert resposta.status_code == 201
    assert resposta.json()["cliente_id"] == ID_MARCOS


def test_simulacao_com_cliente_inexistente_retorna_404(client):
    resposta = client.post("/v1/simulacoes", json={**SIMULACAO, "cliente_id": "nao-existe"})
    assert resposta.status_code == 404
    assert resposta.json()["error"]["code"] == "RECURSO_NAO_ENCONTRADO"


def test_seed_cadastra_a_bandeira_do_mes(client, session_factory):
    with session_factory() as session:
        popular(session)
    atual = client.get("/v1/bandeiras/atual").json()
    assert atual["definida"] is True
    assert atual["bandeira"] == "verde"


def test_patch_de_adesao_atualiza_parcialmente(client, headers_auth, adesao_valida):
    criada = client.post("/v1/adesoes", json=adesao_valida).json()
    resposta = client.patch(f"/v1/adesoes/{criada['id']}", json={"cidade": "Contagem"}, headers=headers_auth)
    assert resposta.status_code == 200
    assert resposta.json()["cidade"] == "Contagem"
    assert resposta.json()["nome"] == criada["nome"]
