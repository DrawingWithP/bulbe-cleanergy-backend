"""
Testes unitários para o módulo de Indicações (IndicacaoService).
O service usa o repositório global, que o conftest zera antes de cada teste.
"""
import pytest
from pydantic import ValidationError

from app.domain.indicacao import IndicacaoCreate, StatusIndicacao
from app.services.indicacao_service import (
    IndicacaoDuplicadaError,
    IndicacaoNaoEncontradaError,
    IndicacaoNaoPodeSerExcluidaError,
    IndicacaoService,
)


@pytest.fixture
def service() -> IndicacaoService:
    return IndicacaoService()


@pytest.fixture
def dados_indicacao() -> IndicacaoCreate:
    return IndicacaoCreate(cliente_id=1, nome="Paula Mendes", contato="paula@email.com")


def test_criar_indicacao_pendente_com_bonus(service: IndicacaoService, dados_indicacao: IndicacaoCreate):
    indicacao = service.criar(dados_indicacao)
    assert indicacao.id == 1
    assert indicacao.situacao == StatusIndicacao.pendente
    assert indicacao.bonus == 50.0


def test_criar_indicacao_com_contato_duplicado(service: IndicacaoService, dados_indicacao: IndicacaoCreate):
    service.criar(dados_indicacao)
    with pytest.raises(IndicacaoDuplicadaError):
        service.criar(dados_indicacao)


def test_contato_duplicado_ignora_maiusculas(service: IndicacaoService, dados_indicacao: IndicacaoCreate):
    """'PAULA@EMAIL.COM' é a mesma pessoa que 'paula@email.com', mesmo indicada por outro cliente."""
    service.criar(dados_indicacao)
    with pytest.raises(IndicacaoDuplicadaError):
        service.criar(IndicacaoCreate(cliente_id=2, nome="Paula", contato="PAULA@EMAIL.COM"))


def test_buscar_indicacao_por_id(service: IndicacaoService, dados_indicacao: IndicacaoCreate):
    criada = service.criar(dados_indicacao)
    assert service.buscar_por_id(1) == criada


def test_buscar_indicacao_inexistente(service: IndicacaoService):
    with pytest.raises(IndicacaoNaoEncontradaError):
        service.buscar_por_id(99)


def test_listar_indicacoes_por_cliente(service: IndicacaoService):
    service.criar(IndicacaoCreate(cliente_id=1, nome="Paula Mendes", contato="paula@email.com"))
    service.criar(IndicacaoCreate(cliente_id=1, nome="Rafael Lima", contato="rafael@email.com"))
    service.criar(IndicacaoCreate(cliente_id=2, nome="Bruna Dias", contato="bruna@email.com"))

    assert [i.nome for i in service.listar_por_cliente(1)] == ["Paula Mendes", "Rafael Lima"]
    assert len(service.listar_por_cliente(2)) == 1
    assert service.listar_por_cliente(3) == []


def test_excluir_indicacao_pendente(service: IndicacaoService, dados_indicacao: IndicacaoCreate):
    service.criar(dados_indicacao)
    service.excluir(1)
    with pytest.raises(IndicacaoNaoEncontradaError):
        service.buscar_por_id(1)


@pytest.mark.parametrize("situacao", [StatusIndicacao.aderiu, StatusIndicacao.cancelada])
def test_excluir_indicacao_nao_pendente(
    service: IndicacaoService, dados_indicacao: IndicacaoCreate, situacao: StatusIndicacao
):
    """Só indicações pendentes podem ser excluídas."""
    indicacao = service.criar(dados_indicacao)
    indicacao.situacao = situacao
    with pytest.raises(IndicacaoNaoPodeSerExcluidaError):
        service.excluir(1)


def test_excluir_indicacao_inexistente(service: IndicacaoService):
    with pytest.raises(IndicacaoNaoEncontradaError):
        service.excluir(99)


@pytest.mark.parametrize(
    "campo, valor",
    [("cliente_id", 0), ("nome", "Pa"), ("contato", "abc")],
)
def test_indicacao_com_campo_invalido_e_rejeitada(campo: str, valor):
    dados = {"cliente_id": 1, "nome": "Paula Mendes", "contato": "paula@email.com"}
    with pytest.raises(ValidationError):
        IndicacaoCreate(**{**dados, campo: valor})
