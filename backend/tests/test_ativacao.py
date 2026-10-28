"""
Testes unitários para o módulo de Ativação CEMIG (US-11 e US-12).
"""
import pytest
from pydantic import ValidationError

from app.domain.ativacao import AtivacaoUpdateRequest, SituacaoEtapa
from app.domain.cliente import Cliente, Endereco, StatusCliente
from app.repositories.ativacao_repository import AtivacaoRepository
from app.repositories.cliente_repository import cliente_repository
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
    """US-12: O Pydantic rejeita etapas fora do range de 1 a 5 (na API vira 422)."""
    with pytest.raises(ValidationError):
        AtivacaoUpdateRequest(etapa_atual=6)
    with pytest.raises(ValidationError):
        AtivacaoUpdateRequest(etapa_atual=0)


@pytest.fixture
def cliente_sem_ativacao() -> Cliente:
    """Cadastra no repositório global um cliente que ainda não tem jornada de ativação."""
    return cliente_repository.criar(
        Cliente(
            id="cliente-novo",
            nome="Lucas Ferreira",
            email="lucas.ferreira@email.com",
            cpf="11122233344",
            telefone="(31) 99999-8888",
            endereco=Endereco(
                cep="30140-071", logradouro="Rua da Bahia", numero="500",
                bairro="Lourdes", cidade="Belo Horizonte", uf="MG",
            ),
            distribuidora="Energisa",
            numero_instalacao="4009876543",
            status=StatusCliente.em_ativacao,
            criado_em="2026-10-01T10:00:00Z",
        )
    )


def test_cliente_sem_jornada_comeca_na_etapa_1(service: AtivacaoService, cliente_sem_ativacao: Cliente):
    """US-11: A jornada é criada na primeira consulta, na etapa 1 e com a distribuidora do cliente."""
    resumo = service.obter_resumo(cliente_sem_ativacao.id)
    assert resumo.etapa_atual == 1
    assert resumo.percentual_concluido == 15
    assert resumo.distribuidora == "Energisa"


def test_listar_etapas_cliente_inexistente(service: AtivacaoService):
    with pytest.raises(ErroDeNegocio) as erro:
        service.listar_etapas("cliente-inexistente-123")
    assert erro.value.status == 404


def test_etapas_concluidas_tem_data_de_conclusao(service: AtivacaoService):
    etapas = service.listar_etapas(CLIENTE_ID_PADRAO).data
    assert etapas[0].concluida_em == "2026-08-18"
    assert etapas[1].concluida_em is None
    assert etapas[4].concluida_em is None


@pytest.mark.parametrize(
    "etapa, percentual",
    [(1, 15), (2, 30), (3, 45), (4, 75), (5, 100)],
)
def test_percentual_de_cada_etapa(service: AtivacaoService, etapa: int, percentual: int):
    """US-12: Cada etapa corresponde a um percentual fixo da jornada."""
    atualizado = service.atualizar_etapa(CLIENTE_ID_PADRAO, AtivacaoUpdateRequest(etapa_atual=etapa))
    assert atualizado.percentual_concluido == percentual


def test_ultima_etapa_marca_todas_anteriores_como_concluidas(service: AtivacaoService):
    service.atualizar_etapa(CLIENTE_ID_PADRAO, AtivacaoUpdateRequest(etapa_atual=5))
    situacoes = [e.situacao for e in service.listar_etapas(CLIENTE_ID_PADRAO).data]
    assert situacoes == [SituacaoEtapa.concluida] * 4 + [SituacaoEtapa.atual]


def test_atualizar_etapa_guarda_observacao(service: AtivacaoService, repository: AtivacaoRepository):
    service.atualizar_etapa(CLIENTE_ID_PADRAO, AtivacaoUpdateRequest(etapa_atual=3, observacao="Protocolo 123"))
    service.atualizar_etapa(CLIENTE_ID_PADRAO, AtivacaoUpdateRequest(etapa_atual=4))
    assert repository.buscar_por_cliente_id(CLIENTE_ID_PADRAO).observacoes == ["Protocolo 123"]


def test_atualizar_etapa_cliente_inexistente(service: AtivacaoService):
    with pytest.raises(ErroDeNegocio) as erro:
        service.atualizar_etapa("cliente-inexistente-123", AtivacaoUpdateRequest(etapa_atual=3))
    assert erro.value.status == 404


def test_service_tambem_valida_etapa_fora_do_intervalo(service: AtivacaoService):
    """O service tem uma segunda barreira (400) caso receba um objeto sem validação do Pydantic."""
    dados_sem_validacao = AtivacaoUpdateRequest.model_construct(etapa_atual=9, observacao=None)
    with pytest.raises(ErroDeNegocio) as erro:
        service.atualizar_etapa(CLIENTE_ID_PADRAO, dados_sem_validacao)
    assert erro.value.status == 400
    assert erro.value.code == "ETAPA_INVALIDA"
