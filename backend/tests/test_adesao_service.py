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



    