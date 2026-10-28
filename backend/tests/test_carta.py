"""
Testes unitários para o Clube Bulbe, Cartas e Cupons (US-18, US-19, US-20 e US-21).
"""
import pytest

from app.domain.carta import SituacaoCarta, TipoCarta
from app.domain.cliente import Cliente, Endereco, StatusCliente
from app.repositories.carta_repository import CartaRepository
from app.repositories.cliente_repository import cliente_repository
from app.repositories.cupom_repository import cupom_repository
from app.services.carta_service import CartaService, ErroDeNegocio


@pytest.fixture
def repository() -> CartaRepository:
    return CartaRepository()


@pytest.fixture
def service(repository: CartaRepository) -> CartaService:
    return CartaService(repository)


CLIENTE_ID_PADRAO = "8f1c2a6e-4b7d-4c1a-9f52-3d6a1b0c7e11"
CARTA_ID_PADRAO = "a7c4e2b9-5d31-4f80-9e6b-8c2a1d4f7b55"


@pytest.fixture
def dados_cliente_novo() -> Cliente:
    """Cadastra no repositório global um cliente sem cartas e sem ofensiva."""
    cliente = Cliente(
        id="cliente-novo",
        nome="Lucas Ferreira",
        email="lucas.ferreira@email.com",
        cpf="11122233344",
        telefone="(31) 99999-8888",
        endereco=Endereco(
            cep="30140-071", logradouro="Rua da Bahia", numero="500",
            bairro="Lourdes", cidade="Belo Horizonte", uf="MG",
        ),
        distribuidora="CEMIG",
        numero_instalacao="4009876543",
        status=StatusCliente.em_ativacao,
        criado_em="2026-10-01T10:00:00Z",
    )
    return cliente_repository.criar(cliente)


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


def test_listar_cartas_cliente_inexistente(service: CartaService):
    """US-19: Retorna 404 para cliente não cadastrado."""
    with pytest.raises(ErroDeNegocio) as erro:
        service.listar_cartas_cliente("cliente-inexistente")
    assert erro.value.status == 404


def test_abrir_carta_agenda_proxima_carta_bloqueada(service: CartaService):
    """US-21: Depois de abrir, a carta da semana seguinte é criada bloqueada."""
    service.abrir_carta(CARTA_ID_PADRAO)

    bloqueadas = service.listar_cartas_cliente(CLIENTE_ID_PADRAO, situacao=SituacaoCarta.bloqueada)
    assert bloqueadas.total == 1
    assert bloqueadas.data[0].semana == 4
    assert bloqueadas.data[0].tipo == TipoCarta.normal


def test_abrir_carta_marca_carta_como_aberta(service: CartaService):
    resultado = service.abrir_carta(CARTA_ID_PADRAO)
    carta = service.buscar_por_id(CARTA_ID_PADRAO)
    assert carta.situacao == SituacaoCarta.aberta
    assert carta.aberta_em is not None
    assert carta.cupom_id == resultado.cupom.id


def test_abrir_carta_salva_cupom_na_carteira_do_cliente(service: CartaService):
    """US-21: O cupom gerado fica disponível no repositório de cupons, válido por 14 dias."""
    resultado = service.abrir_carta(CARTA_ID_PADRAO)
    cupom = cupom_repository.buscar_por_id(resultado.cupom.id)
    assert cupom is not None
    assert cupom.cliente_id == CLIENTE_ID_PADRAO
    assert cupom.carta_id == CARTA_ID_PADRAO
    assert cupom.dias_restantes == 14


def test_quinta_semana_gera_carta_especial(service: CartaService):
    """US-21: Ao completar 5 semanas seguidas, a próxima carta é especial (bônus)."""
    service._sequencias[CLIENTE_ID_PADRAO] = 4

    resultado = service.abrir_carta(CARTA_ID_PADRAO)

    assert resultado.semanas_sequencia == 5
    proxima = service.listar_cartas_cliente(CLIENTE_ID_PADRAO, situacao=SituacaoCarta.bloqueada).data[0]
    assert proxima.tipo == TipoCarta.especial
    assert service.obter_situacao_clube(CLIENTE_ID_PADRAO).bonus_especial_pendente is True


def test_situacao_clube_sem_carta_disponivel(service: CartaService):
    """US-18: Depois de abrir a carta da semana, não há carta disponível e a próxima tem prazo."""
    service.abrir_carta(CARTA_ID_PADRAO)

    situacao = service.obter_situacao_clube(CLIENTE_ID_PADRAO)

    assert situacao.carta_disponivel is False
    assert situacao.semanas_sequencia == 4
    assert situacao.proxima_carta is not None
    assert situacao.proxima_carta.dias_restantes > 0


def test_situacao_clube_cliente_sem_ofensiva(service: CartaService, dados_cliente_novo):
    """Cliente que nunca abriu carta começa com ofensiva zero e sem bônus."""
    situacao = service.obter_situacao_clube(dados_cliente_novo.id)
    assert situacao.semanas_sequencia == 0
    assert situacao.bonus_especial_pendente is False
    assert service.listar_cartas_cliente(dados_cliente_novo.id).total == 0


def test_abrir_carta_inexistente(service: CartaService):
    with pytest.raises(ErroDeNegocio) as erro:
        service.abrir_carta("carta-falsa")
    assert erro.value.status == 404
