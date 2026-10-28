"""
Testes unitários para o módulo de Usinas (UsinaService e validações do domínio).
"""
import pytest
from pydantic import ValidationError

from app.domain.usina import StatusUsina, UsinaCreate, UsinaUpdate
from app.repositories.usina_repository import UsinaRepository
from app.services.usina_service import ErroDeNegocio, UsinaService


@pytest.fixture
def service() -> UsinaService:
    return UsinaService(UsinaRepository())


@pytest.fixture
def dados_usina() -> UsinaCreate:
    return UsinaCreate(
        nome="Usina Solar Uberlandia",
        localizacao="Uberlandia, MG",
        capacidade_geracao_kwh=5000,
    )


def test_criar_usina_com_sucesso(service: UsinaService, dados_usina: UsinaCreate):
    usina = service.criar(dados_usina)
    assert usina.id == 1
    assert usina.nome == "Usina Solar Uberlandia"
    assert usina.status == StatusUsina.ativa
    assert usina.data_ativacao is not None


def test_listar_usinas(service: UsinaService, dados_usina: UsinaCreate):
    assert service.listar() == []
    service.criar(dados_usina)
    service.criar(dados_usina.model_copy(update={"nome": "Usina Solar Montes Claros"}))
    assert [u.id for u in service.listar()] == [1, 2]


def test_buscar_usina_por_id(service: UsinaService, dados_usina: UsinaCreate):
    criada = service.criar(dados_usina)
    assert service.buscar_por_id(1) == criada


def test_buscar_usina_inexistente(service: UsinaService):
    with pytest.raises(ErroDeNegocio) as erro:
        service.buscar_por_id(99)
    assert erro.value.status == 404
    assert erro.value.code == "RECURSO_NAO_ENCONTRADO"


def test_atualizar_usina_parcialmente(service: UsinaService, dados_usina: UsinaCreate):
    """Só os campos enviados mudam; o resto continua igual."""
    service.criar(dados_usina)
    atualizada = service.atualizar(1, UsinaUpdate(status=StatusUsina.em_manutencao))
    assert atualizada.status == StatusUsina.em_manutencao
    assert atualizada.nome == "Usina Solar Uberlandia"
    assert atualizada.capacidade_geracao_kwh == 5000


def test_atualizar_usina_inexistente(service: UsinaService):
    with pytest.raises(ErroDeNegocio) as erro:
        service.atualizar(99, UsinaUpdate(nome="Nova Usina"))
    assert erro.value.status == 404


def test_remover_usina(service: UsinaService, dados_usina: UsinaCreate):
    service.criar(dados_usina)
    service.remover(1)
    assert service.listar() == []


def test_remover_usina_inexistente(service: UsinaService):
    with pytest.raises(ErroDeNegocio) as erro:
        service.remover(99)
    assert erro.value.status == 404


@pytest.mark.parametrize(
    "campo, valor",
    [
        ("nome", "Us"),
        ("localizacao", "BH"),
        ("capacidade_geracao_kwh", 0),
        ("capacidade_geracao_kwh", -100),
        ("status", "desligada"),
    ],
)
def test_usina_com_campo_invalido_e_rejeitada(campo: str, valor):
    dados = {"nome": "Usina Solar", "localizacao": "Uberlandia, MG", "capacidade_geracao_kwh": 5000}
    with pytest.raises(ValidationError):
        UsinaCreate(**{**dados, campo: valor})
