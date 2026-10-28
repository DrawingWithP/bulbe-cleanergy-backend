"""
Testes unitários para o módulo de Parceiros (US-02, US-24, US-25, US-26 e US-33).
"""
import pytest
from app.domain.parceiro import ParceiroCreate, ParceiroUpdate
from app.repositories.parceiro_repository import ParceiroRepository
from app.services.parceiro_service import ErroDeNegocio, ParceiroService


@pytest.fixture
def repository() -> ParceiroRepository:
    return ParceiroRepository()


@pytest.fixture
def service(repository: ParceiroRepository) -> ParceiroService:
    return ParceiroService(repository)


def test_listar_parceiros_sucesso(service: ParceiroService):
    """US-02 / US-33: Lista parceiros cadastrados."""
    resultado = service.listar(page=1, limit=10)
    assert resultado.total >= 2
    assert len(resultado.data) >= 2
    nomes = [p.nome for p in resultado.data]
    assert "Drogaria Araújo" in nomes


def test_criar_parceiro_sucesso(service: ParceiroService):
    """US-24: Cadastra novo parceiro do Clube Bulbe (201 Created)."""
    novo = ParceiroCreate(
        nome="Livelo",
        categoria="Programa de pontos",
        logo_url="https://cdn.bulbeenergia.com.br/parceiros/livelo.svg",
        ativo=True,
    )
    criado = service.criar(novo)
    assert criado.id is not None
    assert criado.nome == "Livelo"
    assert criado.ativo is True


def test_criar_parceiro_duplicado(service: ParceiroService):
    """US-24: Rejeita cadastro de parceiro com nome duplicado (409 Conflict)."""
    novo = ParceiroCreate(
        nome="Drogaria Araújo",
        categoria="Farmácia",
    )
    with pytest.raises(ErroDeNegocio) as erro:
        service.criar(novo)
    assert erro.value.status == 409
    assert erro.value.code == "CONFLITO_DADOS"


def test_buscar_parceiro_por_id_sucesso(service: ParceiroService):
    """US-25: Retorna parceiro por ID com sucesso."""
    parceiro = service.buscar_por_id("1d2c3b4a-5e6f-4071-8293-a4b5c6d7e8f9")
    assert parceiro.nome == "Drogaria Araújo"
    assert parceiro.categoria == "Farmácia"


def test_buscar_parceiro_inexistente(service: ParceiroService):
    """US-25: Retorna 404 ao buscar ID inexistente."""
    with pytest.raises(ErroDeNegocio) as erro:
        service.buscar_por_id("id-inexistente")
    assert erro.value.status == 404
    assert erro.value.code == "RECURSO_NAO_ENCONTRADO"


def test_atualizar_parceiro_sucesso(service: ParceiroService):
    update = ParceiroUpdate(categoria="Farmácia e Saúde", ativo=False)
    atualizado = service.atualizar("1d2c3b4a-5e6f-4071-8293-a4b5c6d7e8f9", update)
    assert atualizado.categoria == "Farmácia e Saúde"
    assert atualizado.ativo is False


def test_remover_parceiro_sucesso(service: ParceiroService):
    """US-26: Remove parceiro com sucesso (204)."""
    service.remover("1d2c3b4a-5e6f-4071-8293-a4b5c6d7e8f9")
    with pytest.raises(ErroDeNegocio):
        service.buscar_por_id("1d2c3b4a-5e6f-4071-8293-a4b5c6d7e8f9")


PARCEIRO_ID_PADRAO = "1d2c3b4a-5e6f-4071-8293-a4b5c6d7e8f9"


@pytest.mark.parametrize("page, limit", [(0, 10), (1, 0), (1, 101)])
def test_listar_parceiros_paginacao_invalida(service: ParceiroService, page: int, limit: int):
    with pytest.raises(ErroDeNegocio) as erro:
        service.listar(page=page, limit=limit)
    assert erro.value.status == 400
    assert erro.value.code == "PARAMETROS_INVALIDOS"


def test_listar_parceiros_filtrando_por_categoria(service: ParceiroService):
    """US-33: O filtro de categoria não diferencia maiúsculas."""
    resultado = service.listar(categoria="BANCO")
    assert [p.nome for p in resultado.data] == ["Banco Inter"]


def test_listar_parceiros_filtrando_por_ativo(service: ParceiroService):
    service.atualizar(PARCEIRO_ID_PADRAO, ParceiroUpdate(ativo=False))
    assert [p.nome for p in service.listar(ativo=True).data] == ["Banco Inter"]
    assert [p.nome for p in service.listar(ativo=False).data] == ["Drogaria Araújo"]


def test_criar_parceiro_duplicado_ignora_maiusculas_e_espacos(service: ParceiroService):
    with pytest.raises(ErroDeNegocio) as erro:
        service.criar(ParceiroCreate(nome="  banco inter ", categoria="Banco"))
    assert erro.value.status == 409


def test_atualizar_parceiro_registra_data_de_atualizacao(service: ParceiroService):
    atualizado = service.atualizar(PARCEIRO_ID_PADRAO, ParceiroUpdate(nome="Araújo"))
    assert atualizado.nome == "Araújo"
    assert atualizado.atualizado_em is not None


def test_atualizar_parceiro_sem_campos_nao_altera_nada(service: ParceiroService):
    atualizado = service.atualizar(PARCEIRO_ID_PADRAO, ParceiroUpdate())
    assert atualizado.atualizado_em is None


def test_atualizar_parceiro_pode_remover_logo(service: ParceiroService):
    """logo_url enviado como null apaga o logo (os outros campos ignoram null)."""
    atualizado = service.atualizar(PARCEIRO_ID_PADRAO, ParceiroUpdate(logo_url=None))
    assert atualizado.logo_url is None


def test_atualizar_parceiro_inexistente(service: ParceiroService):
    with pytest.raises(ErroDeNegocio) as erro:
        service.atualizar("id-inexistente", ParceiroUpdate(nome="Outro"))
    assert erro.value.status == 404


def test_remover_parceiro_inexistente(service: ParceiroService):
    """US-26: Remover um parceiro que não existe retorna 404."""
    with pytest.raises(ErroDeNegocio) as erro:
        service.remover("id-inexistente")
    assert erro.value.status == 404


@pytest.mark.xfail(
    strict=True,
    reason="BUG: ParceiroService.atualizar nao verifica se o novo nome ja pertence a outro parceiro.",
)
def test_renomear_parceiro_para_nome_existente(service: ParceiroService):
    """O cadastro barra nomes duplicados (409), então a atualização deveria barrar também."""
    with pytest.raises(ErroDeNegocio) as erro:
        service.atualizar(PARCEIRO_ID_PADRAO, ParceiroUpdate(nome="Banco Inter"))
    assert erro.value.status == 409
