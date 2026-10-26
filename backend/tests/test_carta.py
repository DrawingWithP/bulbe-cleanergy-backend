"""
Testes unitários para o Clube Bulbe, Cartas e Cupons (US-18, US-19, US-20 e US-21).
"""
import pytest

from app.domain.carta import SituacaoCarta
from app.repositories.carta_repository import CartaRepository
from app.services.carta_service import CartaService, ErroDeNegocio


@pytest.fixture
def repository() -> CartaRepository:
    return CartaRepository()


@pytest.fixture
def service(repository: CartaRepository) -> CartaService:
    return CartaService(repository)


CLIENTE_ID_PADRAO = "8f1c2a6e-4b7d-4c1a-9f52-3d6a1b0c7e11"
CARTA_ID_PADRAO = "a7c4e2b9-5d31-4f80-9e6b-8c2a1d4f7b55"


def test_obter_situacao_clube_sucesso(service: CartaService):
    """US-18: Retorna ofensiva e disponibilidade de carta para cliente existente."""
    situacao = service.obter_situacao_clube(CLIENTE_ID_PADRAO)
    assert situacao.cliente_id == CLIENTE_ID_PADRAO
    assert situacao.meta_sequencia == 5
    assert situacao.intervalo_dias == 7
    assert situacao.carta_disponivel is True


def test_obter_situacao_clube_cliente_inexistente(service: CartaService):
    """US-18: Retorna 404 para cliente não cadastrado."""
    with pytest.raises(ErroDeNegocio) as erro:
        service.obter_situacao_clube("cliente-inexistente")
    assert erro.value.status == 404
    assert erro.value.code == "RECURSO_NAO_ENCONTRADO"


def test_listar_cartas_cliente_sucesso(service: CartaService):
    """US-19: Lista cartas do histórico do cliente."""
    resultado = service.listar_cartas_cliente(CLIENTE_ID_PADRAO)
    assert resultado.total >= 1
    assert resultado.data[0].cliente_id == CLIENTE_ID_PADRAO


def test_buscar_carta_por_id_sucesso(service: CartaService):
    """US-20: Retorna dados da carta pelo ID."""
    carta = service.buscar_por_id(CARTA_ID_PADRAO)
    assert carta.id == CARTA_ID_PADRAO
    assert carta.situacao == SituacaoCarta.disponivel


def test_buscar_carta_inexistente(service: CartaService):
    """US-20: Retorna 404 para carta inexistente."""
    with pytest.raises(ErroDeNegocio) as erro:
        service.buscar_por_id("carta-falsa")
    assert erro.value.status == 404
    assert erro.value.code == "RECURSO_NAO_ENCONTRADO"


def test_abrir_carta_sucesso(service: CartaService):
    """US-21: Abre carta disponível, gera cupom e incrementa ofensiva."""
    resultado = service.abrir_carta(CARTA_ID_PADRAO)
    assert resultado.carta_id == CARTA_ID_PADRAO
    assert resultado.cupom is not None
    assert resultado.cupom.codigo is not None
    assert resultado.semanas_sequencia == 4
    assert resultado.proxima_carta_em is not None


def test_abrir_carta_idempotente(service: CartaService):
    """US-21: Abrir a mesma carta duas vezes retorna o mesmo cupom sem erros."""
    resultado1 = service.abrir_carta(CARTA_ID_PADRAO)
    resultado2 = service.abrir_carta(CARTA_ID_PADRAO)
    assert resultado1.cupom.id == resultado2.cupom.id


def test_abrir_carta_nao_disponivel(service: CartaService):
    """US-21: Retorna 409 ao tentar abrir uma carta bloqueada."""
    service.abrir_carta(CARTA_ID_PADRAO)
    carta = service.buscar_por_id(CARTA_ID_PADRAO)
    carta.situacao = SituacaoCarta.bloqueada
    service._repository.atualizar(carta)

    with pytest.raises(ErroDeNegocio) as erro:
        service.abrir_carta(CARTA_ID_PADRAO)
    assert erro.value.status == 409
    assert erro.value.code == "CARTA_NAO_DISPONIVEL"
