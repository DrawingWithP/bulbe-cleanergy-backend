"""
Testes unitários para o módulo de Cupons (US-03, US-22 e US-23).
"""
import pytest
from app.domain.cupom import CupomUpdate, SituacaoCupom
from app.repositories.cupom_repository import CupomRepository
from app.services.cupom_service import CupomService, ErroDeNegocio


@pytest.fixture
def repository() -> CupomRepository:
    return CupomRepository()


@pytest.fixture
def service(repository: CupomRepository) -> CupomService:
    return CupomService(repository)


CLIENTE_ID_PADRAO = "8f1c2a6e-4b7d-4c1a-9f52-3d6a1b0c7e11"
CUPOM_ID_PADRAO = "f6b1d803-2e94-4a57-83cd-9b0e5a7c1d22"


def test_listar_cupons_cliente_sucesso(service: CupomService):
    """US-03: Retorna a lista de cupons de um cliente."""
    resultado = service.listar_por_cliente(CLIENTE_ID_PADRAO)
    assert resultado.total >= 1
    assert resultado.data[0].codigo == "BULBE15"


def test_listar_cupons_cliente_inexistente(service: CupomService):
    """US-03: Retorna 404 caso o cliente não exista."""
    with pytest.raises(ErroDeNegocio) as erro:
        service.listar_por_cliente("cliente-falso")
    assert erro.value.status == 404
    assert erro.value.code == "RECURSO_NAO_ENCONTRADO"


def test_buscar_cupom_por_id_sucesso(service: CupomService):
    """US-22: Retorna dados do cupom por ID."""
    cupom = service.buscar_por_id(CUPOM_ID_PADRAO)
    assert cupom.id == CUPOM_ID_PADRAO
    assert cupom.parceiro.nome == "Drogaria Araújo"


def test_buscar_cupom_inexistente(service: CupomService):
    """US-22: Retorna 404 ao buscar cupom inexistente."""
    with pytest.raises(ErroDeNegocio) as erro:
        service.buscar_por_id("cupom-falso")
    assert erro.value.status == 404
    assert erro.value.code == "RECURSO_NAO_ENCONTRADO"


def test_atualizar_situacao_para_salvo(service: CupomService):
    """US-23: Atualiza situação do cupom para 'salvo'."""
    update = CupomUpdate(situacao=SituacaoCupom.salvo)
    atualizado = service.atualizar_situacao(CUPOM_ID_PADRAO, update)
    assert atualizado.situacao == SituacaoCupom.salvo


def test_atualizar_situacao_para_usado(service: CupomService):
    """US-23: Marca cupom como utilizado ('usado') e registra data."""
    update = CupomUpdate(situacao=SituacaoCupom.usado)
    atualizado = service.atualizar_situacao(CUPOM_ID_PADRAO, update)
    assert atualizado.situacao == SituacaoCupom.usado
    assert atualizado.usado_em is not None


def test_descartar_cupom_sucesso(service: CupomService):
    service.descartar(CUPOM_ID_PADRAO)
    with pytest.raises(ErroDeNegocio):
        service.buscar_por_id(CUPOM_ID_PADRAO)
