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


@pytest.mark.parametrize("page, limit", [(0, 10), (1, 0), (1, 101)])
def test_listar_cupons_paginacao_invalida(service: CupomService, page: int, limit: int):
    with pytest.raises(ErroDeNegocio) as erro:
        service.listar_por_cliente(CLIENTE_ID_PADRAO, page=page, limit=limit)
    assert erro.value.status == 400
    assert erro.value.code == "PARAMETROS_INVALIDOS"


def test_listar_cupons_filtrando_por_situacao(service: CupomService):
    """US-03: O filtro por situação devolve só os cupons naquela situação."""
    assert service.listar_por_cliente(CLIENTE_ID_PADRAO, situacao=SituacaoCupom.ativo).total == 1
    assert service.listar_por_cliente(CLIENTE_ID_PADRAO, situacao=SituacaoCupom.salvo).total == 0


@pytest.mark.parametrize(
    "situacao",
    [SituacaoCupom.ativo, SituacaoCupom.expirado, SituacaoCupom.descartado],
)
def test_atualizar_situacao_nao_permitida(service: CupomService, situacao: SituacaoCupom):
    """US-23: Só é possível mudar para 'salvo' ou 'usado'."""
    with pytest.raises(ErroDeNegocio) as erro:
        service.atualizar_situacao(CUPOM_ID_PADRAO, CupomUpdate(situacao=situacao))
    assert erro.value.status == 400
    assert erro.value.code == "SITUACAO_INVALIDA"


def test_cupom_usado_nao_volta_para_salvo(service: CupomService):
    """US-23: Um cupom já usado não pode ter a situação alterada."""
    service.atualizar_situacao(CUPOM_ID_PADRAO, CupomUpdate(situacao=SituacaoCupom.usado))
    with pytest.raises(ErroDeNegocio) as erro:
        service.atualizar_situacao(CUPOM_ID_PADRAO, CupomUpdate(situacao=SituacaoCupom.salvo))
    assert erro.value.status == 409
    assert erro.value.code == "CUPOM_JA_UTILIZADO"


def test_atualizar_situacao_cupom_inexistente(service: CupomService):
    with pytest.raises(ErroDeNegocio) as erro:
        service.atualizar_situacao("cupom-falso", CupomUpdate(situacao=SituacaoCupom.salvo))
    assert erro.value.status == 404


def test_cupom_descartado_some_da_listagem(service: CupomService):
    """O descarte é lógico: o cupom continua guardado, mas não aparece mais para o cliente."""
    service.descartar(CUPOM_ID_PADRAO)
    assert service.listar_por_cliente(CLIENTE_ID_PADRAO).total == 0


def test_descartar_cupom_inexistente(service: CupomService):
    with pytest.raises(ErroDeNegocio) as erro:
        service.descartar("cupom-falso")
    assert erro.value.status == 404
