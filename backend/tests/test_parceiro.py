"""
Testes unitários para o módulo de Parceiros (US-02, US-24, US-25, US-26 e US-33).
"""
import pytest
from app.domain.parceiro import ParceiroCreate, ParceiroUpdate
from app.repositories.parceiro_repository import ParceiroRepository
from app.services.parceiro_service import ErroDeNegocio, ParceiroService


@pytest.fixture
def repository() -> ParceiroRepository:
    return ParceiroRepository()


@pytest.fixture
def service(repository: ParceiroRepository) -> ParceiroService:
    return ParceiroService(repository)


def test_listar_parceiros_sucesso(service: ParceiroService):
    """US-02 / US-33: Lista parceiros cadastrados."""
    resultado = service.listar(page=1, limit=10)
    assert resultado.total >= 2
    assert len(resultado.data) >= 2
    nomes = [p.nome for p in resultado.data]
    assert "Drogaria Araújo" in nomes


def test_criar_parceiro_sucesso(service: ParceiroService):
    """US-24: Cadastra novo parceiro do Clube Bulbe (201 Created)."""
    novo = ParceiroCreate(
        nome="Livelo",
        categoria="Programa de pontos",
        logo_url="https://cdn.bulbeenergia.com.br/parceiros/livelo.svg",
        ativo=True,
    )
    criado = service.criar(novo)
    assert criado.id is not None
    assert criado.nome == "Livelo"
    assert criado.ativo is True


def test_criar_parceiro_duplicado(service: ParceiroService):
    """US-24: Rejeita cadastro de parceiro com nome duplicado (409 Conflict)."""
    novo = ParceiroCreate(
        nome="Drogaria Araújo",
        categoria="Farmácia",
    )
    with pytest.raises(ErroDeNegocio) as erro:
        service.criar(novo)
    assert erro.value.status == 409
    assert erro.value.code == "CONFLITO_DADOS"


def test_buscar_parceiro_por_id_sucesso(service: ParceiroService):
    """US-25: Retorna parceiro por ID com sucesso."""
    parceiro = service.buscar_por_id("1d2c3b4a-5e6f-4071-8293-a4b5c6d7e8f9")
    assert parceiro.nome == "Drogaria Araújo"
    assert parceiro.categoria == "Farmácia"


def test_buscar_parceiro_inexistente(service: ParceiroService):
    """US-25: Retorna 404 ao buscar ID inexistente."""
    with pytest.raises(ErroDeNegocio) as erro:
        service.buscar_por_id("id-inexistente")
    assert erro.value.status == 404
    assert erro.value.code == "RECURSO_NAO_ENCONTRADO"


def test_atualizar_parceiro_sucesso(service: ParceiroService):
    update = ParceiroUpdate(categoria="Farmácia e Saúde", ativo=False)
    atualizado = service.atualizar("1d2c3b4a-5e6f-4071-8293-a4b5c6d7e8f9", update)
    assert atualizado.categoria == "Farmácia e Saúde"
    assert atualizado.ativo is False


def test_remover_parceiro_sucesso(service: ParceiroService):
    """US-26: Remove parceiro com sucesso (204)."""
    service.remover("1d2c3b4a-5e6f-4071-8293-a4b5c6d7e8f9")
    with pytest.raises(ErroDeNegocio):
        service.buscar_por_id("1d2c3b4a-5e6f-4071-8293-a4b5c6d7e8f9")
