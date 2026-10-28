from unittest.mock import Mock

import pytest

from app.domain.adesao import StatusAdesao, AdesaoCreate, AdesaoUpdate
from app.repositories.adesao_repository import AdesaoRepository
from app.services.adesao_service import ErroDeNegocio, AdesaoService

@pytest.fixture
def service() -> AdesaoService:
    return AdesaoService(AdesaoRepository())


@pytest.fixture
def dados_adesao() -> AdesaoCreate:
    return AdesaoCreate(nome="João da Silva", email="joaosilva@gmail.com", cpf="14444444444", telefone="999999999", cep="34331312", logradouro="Rua Oliveira", numero=213, bairro="Buritis",cidade="Belo Horizonte", uf="MG", distribuidora="Cemig", numero_instalacao="3242412", valor_conta_atual=399.00)

def test_criar_adesao_com_mesmo_cpf(service, dados_adesao):
    adesao = service.criar(dados_adesao)

    with pytest.raises(ErroDeNegocio) as erro:
        adesao2 = service.criar(dados_adesao)
    assert erro.value.status == 409

def test_consultar_adesao_por_id(service, dados_adesao):
    adesao = service.criar(dados_adesao)

    assert service.buscar_por_id(1) == adesao

def test_atualizar_dados_adesao(service, dados_adesao):
    adesao = service.criar(dados_adesao)
    
    dadosAtualizados = dados_adesao
    dadosAtualizados.telefone = "988888888"
    service.atualizar(1,dadosAtualizados)

    assert service.buscar_por_id(1).telefone == "988888888"

def test_criar_adesao_com_sucesso(service, dados_adesao):
    adesao = service.criar(dados_adesao)

    assert adesao.id == 1
    assert adesao.cpf == "14444444444"
    assert adesao.status == StatusAdesao.enviada
    assert adesao.data_ativacao is not None


def test_criar_adesao_com_mesmo_cpf_retorna_codigo_do_erro(service, dados_adesao):
    service.criar(dados_adesao)

    with pytest.raises(ErroDeNegocio) as erro:
        service.criar(dados_adesao)
    assert erro.value.code == "CPF_INVALIDO"


def test_ids_sao_sequenciais(service, dados_adesao):
    primeira = service.criar(dados_adesao)
    segunda = service.criar(dados_adesao.model_copy(update={"cpf": "15555555555"}))

    assert (primeira.id, segunda.id) == (1, 2)


def test_listar_adesoes_vazio(service):
    assert service.listar() == []


def test_listar_adesoes(service, dados_adesao):
    service.criar(dados_adesao)
    service.criar(dados_adesao.model_copy(update={"cpf": "15555555555"}))

    assert len(service.listar()) == 2


def test_consultar_adesao_inexistente(service):
    with pytest.raises(ErroDeNegocio) as erro:
        service.buscar_por_id(99)
    assert erro.value.status == 404
    assert erro.value.code == "RECURSO_NAO_ENCONTRADO"


def test_atualizar_adesao_inexistente(service, dados_adesao):
    with pytest.raises(ErroDeNegocio) as erro:
        service.atualizar(99, dados_adesao)
    assert erro.value.status == 404


def test_atualizar_status_da_adesao(service, dados_adesao):
    service.criar(dados_adesao)
    # Hoje o AdesaoUpdate exige nome, email, cpf e telefone (ver xfail em test_adesao_domain.py).
    atualizacao = AdesaoUpdate(
        nome="João da Silva",
        email="joaosilva@gmail.com",
        cpf="14444444444",
        telefone="988888888",
        status=StatusAdesao.aprovada,
    )

    atualizada = service.atualizar(1, atualizacao)

    assert atualizada.status == StatusAdesao.aprovada
    assert atualizada.telefone == "988888888"
    assert atualizada.cidade == "Belo Horizonte"


def test_remover_adesao(service, dados_adesao):
    service.criar(dados_adesao)
    service.remover(1)

    with pytest.raises(ErroDeNegocio) as erro:
        service.buscar_por_id(1)
    assert erro.value.status == 404


def test_remover_adesao_inexistente(service):
    with pytest.raises(ErroDeNegocio) as erro:
        service.remover(99)
    assert erro.value.status == 404
    assert erro.value.code == "RECURSO_NAO_ENCONTRADO"


def test_service_usa_o_repositorio_recebido():
    """O service delega a listagem ao repositório injetado (teste com Mock)."""
    repositorio_falso = Mock()
    repositorio_falso.listar.return_value = ["adesao-falsa"]

    assert AdesaoService(repositorio_falso).listar() == ["adesao-falsa"]
    repositorio_falso.listar.assert_called_once()
