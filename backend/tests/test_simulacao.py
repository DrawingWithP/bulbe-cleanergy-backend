"""
Testes unitários e de integração (HTTP) para o módulo de Simulação de economia.
"""
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.domain.simulacao import SimulacaoCreate
from app.repositories.simulacao_repository import SimulacaoRepository
from app.services.simulacao_service import ErroDeNegocio, SimulacaoService

SIMULACAO = {"valor_atual": 350.0, "valor_proposto": 280.0, "periodo_meses": 12, "indicacoes": 2}


@pytest.fixture
def service() -> SimulacaoService:
    return SimulacaoService(SimulacaoRepository())


def test_criar_simulacao(service: SimulacaoService):
    simulacao = service.criar(SimulacaoCreate(**SIMULACAO))
    assert simulacao.id == 1
    assert simulacao.valor_atual == 350.0
    assert simulacao.data_ativacao is not None


def test_listar_e_buscar_simulacao(service: SimulacaoService):
    criada = service.criar(SimulacaoCreate(**SIMULACAO))
    assert service.listar() == [criada]
    assert service.buscar_por_id(1) == criada


def test_buscar_simulacao_inexistente(service: SimulacaoService):
    with pytest.raises(ErroDeNegocio) as erro:
        service.buscar_por_id(99)
    assert erro.value.status == 404
    assert erro.value.code == "RECURSO_NAO_ENCONTRADO"


def test_remover_simulacao(service: SimulacaoService):
    service.criar(SimulacaoCreate(**SIMULACAO))
    service.remover(1)
    assert service.listar() == []


def test_remover_simulacao_inexistente(service: SimulacaoService):
    with pytest.raises(ErroDeNegocio) as erro:
        service.remover(99)
    assert erro.value.status == 404


def test_valor_proposto_pode_ser_zero():
    """valor_proposto usa ge=0, então zero é aceito."""
    assert SimulacaoCreate(**{**SIMULACAO, "valor_proposto": 0}).valor_proposto == 0


@pytest.mark.parametrize(
    "campo, valor",
    [
        ("valor_atual", 0),
        ("valor_proposto", -1),
        ("periodo_meses", 0),
        ("indicacoes", 0),
    ],
)
def test_simulacao_com_campo_invalido_e_rejeitada(campo: str, valor):
    with pytest.raises(ValidationError):
        SimulacaoCreate(**{**SIMULACAO, campo: valor})


def test_api_criar_simulacao_retorna_201(client: TestClient):
    resposta = client.post("/v1/simulacaos", json=SIMULACAO)
    assert resposta.status_code == 201
    assert resposta.json()["id"] == 1


def test_api_criar_simulacao_invalida_retorna_422(client: TestClient):
    resposta = client.post("/v1/simulacaos", json={**SIMULACAO, "valor_atual": -5})
    assert resposta.status_code == 422
