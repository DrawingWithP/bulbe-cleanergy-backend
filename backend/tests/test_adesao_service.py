from unittest.mock import Mock

import pytest

from app.domain.adesao import StatusAdesao, AdesaoCreate, AdesaoUpdate
from app.repositories.adesao_repository import AdesaoRepository
from app.services.adesao_service import ErroDeNegocio, AdesaoService

@pytest.fixture
def service() -> AdesaoService:
    return AdesaoService(AdesaoRepository())


@pytest.fixture
def dados_usina() -> AdesaoCreate:
    return AdesaoCreate(nome="João da Silva", email="joaosilva@gmail.com", telefone="999999999", cep="34331312", logradouro="Rua Oliveira", numero=213, bairro="Buritis",cidade="Belo Horizonte", uf="MG", distribuidora="Cemig", numero_instalacao="3242412", valor_conta_atual=399.00)

def test_criar_adesao_com_mesmo_cpf(service, dados_adesao):
    adesao = service.criar(dados_adesao)

    with pytest.raises(ErroDeNegocio) as erro:
        adesao2 = service.criar(dados_adesao)
    assert erro.value.code == 409
    