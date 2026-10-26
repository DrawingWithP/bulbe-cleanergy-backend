"""
Testes unitários para o módulo de Clientes (US-05, US-31 e US-34).
"""
import pytest
from app.domain.cliente import ClienteCreate, ClienteUpdate, Endereco, EnderecoUpdate, StatusCliente
from app.repositories.cliente_repository import ClienteRepository
from app.services.cliente_service import ClienteService, ErroDeNegocio


@pytest.fixture
def repository() -> ClienteRepository:
    return ClienteRepository()


@pytest.fixture
def service(repository: ClienteRepository) -> ClienteService:
    return ClienteService(repository)


@pytest.fixture
def dados_cliente() -> ClienteCreate:
    return ClienteCreate(
        nome="Lucas Ferreira",
        email="lucas.ferreira@email.com",
        cpf="11122233344",
        telefone="(31) 99999-8888",
        endereco=Endereco(
            cep="30140-071",
            logradouro="Rua da Bahia",
            numero="500",
            bairro="Lourdes",
            cidade="Belo Horizonte",
            uf="MG",
        ),
        distribuidora="CEMIG",
        numero_instalacao="4009876543",
    )


def test_criar_cliente_com_sucesso(service: ClienteService):
    """US-31: Cadastra um novo cliente com sucesso (201 Created)."""
    novo = ClienteCreate(
        nome="Mariana Costa",
        email="mariana.costa@email.com",
        cpf="22233344455",
        telefone="(31) 98765-4321",
        endereco=Endereco(
            cep="30130-110",
            logradouro="Rua Sergipe",
            numero="800",
            bairro="Funcionários",
            cidade="Belo Horizonte",
            uf="MG",
        ),
        distribuidora="CEMIG",
        numero_instalacao="5001234567",
    )
    resultado = service.criar(novo)
    assert resultado.id is not None
    assert resultado.nome == "Mariana Costa"
    assert resultado.status == StatusCliente.em_ativacao


def test_criar_cliente_com_cpf_duplicado(service: ClienteService, dados_cliente: ClienteCreate):
    """US-31: Impede cadastro com CPF já existente (409 Conflict)."""
    service.criar(dados_cliente)
    with pytest.raises(ErroDeNegocio) as erro:
        service.criar(dados_cliente)
    assert erro.value.status == 409
    assert erro.value.code == "CONFLITO_DADOS"


def test_buscar_cliente_por_id_sucesso(service: ClienteService):
    """US-05: Consulta cliente cadastrado por ID (200 OK)."""
    cliente = service.buscar_por_id("8f1c2a6e-4b7d-4c1a-9f52-3d6a1b0c7e11")
    assert cliente.nome == "Marcos Andrade"
    assert cliente.email == "marcos.andrade@email.com"


def test_buscar_cliente_inexistente(service: ClienteService):
    """US-05: Retorna 404 ao buscar ID inexistente."""
    with pytest.raises(ErroDeNegocio) as erro:
        service.buscar_por_id("id-inexistente")
    assert erro.value.status == 404
    assert erro.value.code == "RECURSO_NAO_ENCONTRADO"


def test_atualizar_cliente_sucesso(service: ClienteService):
    """US-34: Atualiza dados cadastrais do cliente (200 OK)."""
    update = ClienteUpdate(
        telefone="(31) 91111-2222",
        endereco=EnderecoUpdate(numero="1050", complemento="Apto 501"),
    )
    atualizado = service.atualizar("8f1c2a6e-4b7d-4c1a-9f52-3d6a1b0c7e11", update)
    assert atualizado.telefone == "(31) 91111-2222"
    assert atualizado.endereco.numero == "1050"
    assert atualizado.endereco.complemento == "Apto 501"


def test_listar_clientes_com_paginacao(service: ClienteService):
    resultado = service.listar(page=1, limit=10)
    assert resultado.total >= 1
    assert len(resultado.data) >= 1
    assert resultado.data[0].nome == "Marcos Andrade"


def test_remover_cliente_sucesso(service: ClienteService):
    service.remover("8f1c2a6e-4b7d-4c1a-9f52-3d6a1b0c7e11")
    with pytest.raises(ErroDeNegocio):
        service.buscar_por_id("8f1c2a6e-4b7d-4c1a-9f52-3d6a1b0c7e11")
