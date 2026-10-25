"""
Testes unitários para o módulo de Ativação CEMIG (US-11 e US-12).
"""
import pytest
from app.domain.ativacao import AtivacaoUpdateRequest, SituacaoEtapa
from app.repositories.ativacao_repository import AtivacaoRepository
from app.services.ativacao_service import AtivacaoService, ErroDeNegocio


@pytest.fixture
def repository() -> AtivacaoRepository:
    return AtivacaoRepository()


@pytest.fixture
def service(repository: AtivacaoRepository) -> AtivacaoService:
    return AtivacaoService(repository)


CLIENTE_ID_PADRAO = "8f1c2a6e-4b7d-4c1a-9f52-3d6a1b0c7e11"


def test_obter_resumo_ativacao_sucesso(service: AtivacaoService):
    """US-11: Retorna resumo do status de ativação com percentual e prazos."""
    resumo = service.obter_resumo(CLIENTE_ID_PADRAO)
    assert resumo.cliente_id == CLIENTE_ID_PADRAO
    assert resumo.etapa_atual == 2
    assert resumo.percentual_concluido == 30
    assert resumo.total_etapas == 5
    assert "CEMIG" in resumo.distribuidora


def test_obter_resumo_cliente_inexistente(service: AtivacaoService):
    """US-11: Retorna 404 caso o cliente não seja encontrado."""
    with pytest.raises(ErroDeNegocio) as erro:
        service.obter_resumo("cliente-inexistente-123")
    assert erro.value.status == 404
    assert erro.value.code == "RECURSO_NAO_ENCONTRADO"


def test_listar_etapas_ativacao_sucesso(service: AtivacaoService):
    """Retorna as 5 etapas com status correto (concluída, atual, pendente)."""
    etapas_resp = service.listar_etapas(CLIENTE_ID_PADRAO)
    assert etapas_resp.total == 5
    assert len(etapas_resp.data) == 5

    # Para cliente na etapa 2: etapa 1 concluída, etapa 2 atual, etapa 3 pendente
    assert etapas_resp.data[0].situacao == SituacaoEtapa.concluida
    assert etapas_resp.data[1].situacao == SituacaoEtapa.atual
    assert etapas_resp.data[2].situacao == SituacaoEtapa.pendente


def test_atualizar_etapa_ativacao_sucesso(service: AtivacaoService):
    """US-12: Atualiza a etapa atual e reflete o novo percentual."""
    dados = AtivacaoUpdateRequest(etapa_atual=3, observacao="Protocolo CEMIG aberto.")
    atualizado = service.atualizar_etapa(CLIENTE_ID_PADRAO, dados)

    assert atualizado.etapa_atual == 3
    assert atualizado.percentual_concluido == 45
    assert "Solicitação enviada" in atualizado.titulo


def test_atualizar_etapa_invalida(service: AtivacaoService):
    """US-12: Rejeita etapas fora do range de 1 a 5 com erro 400."""
    with pytest.raises(Exception):
        AtivacaoUpdateRequest(etapa_atual=6)
