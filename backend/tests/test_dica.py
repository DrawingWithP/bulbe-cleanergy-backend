"""
Testes unitários para o módulo de Dicas de economia (DicaService, US-30).
"""
import pytest
from pydantic import ValidationError

from app.domain.dica import DicaCreate, DicaUpdate
from app.repositories.dica_repository import DicaRepository
from app.services.dica_service import DicaService, ErroDeNegocio

SVG = "<svg xmlns='http://www.w3.org/2000/svg'></svg>"


@pytest.fixture
def service() -> DicaService:
    return DicaService(DicaRepository())


@pytest.fixture
def dados_dica() -> DicaCreate:
    return DicaCreate(
        titulo="Desligue o ar-condicionado",
        descricao="Desligue o ar-condicionado ao sair do ambiente.",
        economia=35.5,
        imagem_svg=SVG,
    )


def test_criar_dica_com_sucesso(service: DicaService, dados_dica: DicaCreate):
    dica = service.criar(dados_dica)
    assert dica.id == 1
    assert dica.economia == 35.5
    assert dica.imagem_svg == SVG


def test_listar_dicas(service: DicaService, dados_dica: DicaCreate):
    assert service.listar() == []
    service.criar(dados_dica)
    assert len(service.listar()) == 1


def test_buscar_dica_por_id(service: DicaService, dados_dica: DicaCreate):
    criada = service.criar(dados_dica)
    assert service.buscar_por_id(1) == criada


def test_buscar_dica_inexistente(service: DicaService):
    with pytest.raises(ErroDeNegocio) as erro:
        service.buscar_por_id(99)
    assert erro.value.status == 404
    assert erro.value.code == "RECURSO_NAO_ENCONTRADO"


def test_atualizar_dica_parcialmente(service: DicaService, dados_dica: DicaCreate):
    service.criar(dados_dica)
    atualizada = service.atualizar(1, DicaUpdate(economia=50))
    assert atualizada.economia == 50
    assert atualizada.titulo == "Desligue o ar-condicionado"


def test_atualizar_dica_inexistente(service: DicaService):
    with pytest.raises(ErroDeNegocio) as erro:
        service.atualizar(99, DicaUpdate(titulo="Nova dica"))
    assert erro.value.status == 404


def test_remover_dica(service: DicaService, dados_dica: DicaCreate):
    """US-30: Remove uma dica específica."""
    service.criar(dados_dica)
    service.remover(1)
    with pytest.raises(ErroDeNegocio):
        service.buscar_por_id(1)


def test_remover_dica_inexistente(service: DicaService):
    with pytest.raises(ErroDeNegocio) as erro:
        service.remover(99)
    assert erro.value.status == 404


@pytest.mark.parametrize(
    "campo, valor",
    [
        ("titulo", "ab"),
        ("descricao", "ab"),
        ("descricao", "x" * 251),
        ("economia", 0),
    ],
)
def test_dica_com_campo_invalido_e_rejeitada(campo: str, valor):
    dados = {"titulo": "Dica", "descricao": "Descrição", "economia": 10, "imagem_svg": SVG}
    with pytest.raises(ValidationError):
        DicaCreate(**{**dados, campo: valor})
