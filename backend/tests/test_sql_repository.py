"""
Testes de integracao dos repositorios SQL, contra o banco de teste (bulbe_test.db).

Cada teste abre repositorios NOVOS para ler o que outro gravou: e o equivalente
a "reiniciar a API" e conferir que o dado continua la.
"""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.db.models import AtivacaoModel, CartaModel, CupomModel, OfensivaClubeModel
from app.db.seed import ID_CARTA_MARCOS, ID_MARCOS, popular
from app.domain.ativacao import AtivacaoCliente
from app.domain.cupom import Cupom, ParceiroResumoCupom
from app.domain.primeiro_acesso import Verificacao
from app.domain.usina import StatusUsina, UsinaCreate, UsinaUpdate
from app.repositories.ativacao_repository import SqlAtivacaoRepository
from app.repositories.carta_repository import SqlCartaRepository
from app.repositories.cliente_repository import SqlClienteRepository
from app.repositories.cupom_repository import SqlCupomRepository
from app.repositories.parceiro_repository import SqlParceiroRepository
from app.repositories.primeiro_acesso_repository import SqlPrimeiroAcessoRepository
from app.repositories.usina_repository import SqlUsinaRepository
from app.repositories.usuario_repository import SqlUsuarioRepository


@pytest.fixture
def com_seed(session_factory):
    with session_factory() as session:
        popular(session)


def _usina() -> UsinaCreate:
    return UsinaCreate(nome="Usina Solar Janauba", localizacao="Janauba, MG", capacidade_geracao_kwh=7800)


def test_dado_persiste_entre_instancias_do_repositorio(session_factory):
    criada = SqlUsinaRepository(session_factory).criar(_usina())

    # Outra instancia, outra sessao: so acha a usina se o commit gravou de verdade.
    lida = SqlUsinaRepository(session_factory).buscar_por_id(criada.id)

    assert lida is not None
    assert lida.id == 1
    assert lida.nome == "Usina Solar Janauba"


def test_atualizar_status_persiste_no_banco(session_factory):
    criada = SqlUsinaRepository(session_factory).criar(_usina())

    SqlUsinaRepository(session_factory).atualizar(criada.id, UsinaUpdate(status=StatusUsina.em_manutencao))

    assert SqlUsinaRepository(session_factory).buscar_por_id(criada.id).status == StatusUsina.em_manutencao


def test_remover_apaga_a_linha_do_banco(session_factory):
    criada = SqlUsinaRepository(session_factory).criar(_usina())

    assert SqlUsinaRepository(session_factory).remover(criada.id) is True
    assert SqlUsinaRepository(session_factory).listar() == []
    assert SqlUsinaRepository(session_factory).remover(criada.id) is False


def test_email_de_usuario_e_unico_no_banco(session_factory):
    repo = SqlUsuarioRepository(session_factory)
    repo.criar("Operadora", "operacao@bulbe.com.br", "hash")

    with pytest.raises(IntegrityError):
        repo.criar("Outra", "OPERACAO@bulbe.com.br", "hash")


def test_fk_impede_cupom_de_cliente_inexistente(session_factory):
    cupom = Cupom(
        id="cupom-orfao",
        cliente_id="cliente-que-nao-existe",
        titulo="Cupom sem dono",
        descricao="Nao deveria ser gravado.",
        codigo="ORFAO1",
        parceiro=ParceiroResumoCupom(id="p1", nome="Parceiro", categoria="Teste"),
        valido_ate="2026-12-31",
        criado_em="2026-11-01T00:00:00Z",
    )

    with pytest.raises(IntegrityError):
        SqlCupomRepository(session_factory).salvar(cupom)


def test_remover_cliente_apaga_filhos_em_cascata(session_factory, com_seed):
    assert SqlClienteRepository(session_factory).remover(ID_MARCOS) is True

    with session_factory() as session:
        for modelo in (AtivacaoModel, CartaModel, CupomModel, OfensivaClubeModel):
            restantes = session.scalars(select(modelo).where(modelo.cliente_id == ID_MARCOS)).all()
            assert restantes == [], f"{modelo.__tablename__} deveria ter sido apagada em cascata"


def test_ativacao_guarda_observacoes_entre_sessoes(session_factory, com_seed):
    repo = SqlAtivacaoRepository(session_factory)
    ativacao = repo.buscar_por_cliente_id(ID_MARCOS)
    ativacao.etapa_atual = 3
    ativacao.observacoes.append("Protocolo CEMIG aberto.")
    repo.salvar_ou_atualizar(ativacao)

    lida = SqlAtivacaoRepository(session_factory).buscar_por_cliente_id(ID_MARCOS)

    assert lida.etapa_atual == 3
    assert lida.observacoes == ["Protocolo CEMIG aberto."]


def test_ativacao_exige_cliente_existente(session_factory):
    ativacao = AtivacaoCliente(cliente_id="nao-existe", atualizado_em="2026-11-01T00:00:00Z")

    with pytest.raises(IntegrityError):
        SqlAtivacaoRepository(session_factory).salvar_ou_atualizar(ativacao)


def test_primeiro_acesso_habilita_o_cliente_da_tabela_clientes(session_factory, com_seed):
    repo = SqlPrimeiroAcessoRepository(session_factory)
    cliente = repo.buscar_cliente_por_cpf("529.982.247-25")
    agora = datetime.now(timezone.utc)
    repo.salvar_verificacao(
        Verificacao(
            id="verif-1", cliente_id=cliente["id"], cpf=cliente["cpf"], canal="whatsapp",
            codigo="123456", destino_mascarado="(31) *****-1234",
            expira_em=agora + timedelta(minutes=15), criado_em=agora,
        )
    )

    lida = SqlPrimeiroAcessoRepository(session_factory).buscar_verificacao_por_id("verif-1")
    repo.habilitar_acesso_cliente(cliente["id"])

    assert lida.codigo == "123456"
    assert lida.expira_em.tzinfo is not None
    assert SqlClienteRepository(session_factory).buscar_por_id(ID_MARCOS).acesso_habilitado is True


def test_ofensiva_e_cartas_do_clube_persistem(session_factory, com_seed):
    repo = SqlCartaRepository(session_factory)
    repo.salvar_sequencia(ID_MARCOS, 4)

    novo_repo = SqlCartaRepository(session_factory)

    assert novo_repo.obter_sequencia(ID_MARCOS) == 4
    assert novo_repo.buscar_disponivel_cliente(ID_MARCOS).id == ID_CARTA_MARCOS


def test_parceiros_paginacao_e_filtros(session_factory, com_seed):
    repo = SqlParceiroRepository(session_factory)

    pagina, total = repo.listar(page=1, limit=2)
    farmacias, total_farmacias = repo.listar(categoria="farmácia")

    assert total == 3
    assert len(pagina) == 2
    assert total_farmacias == 1
    assert farmacias[0].nome == "Drogaria Araújo"
    assert repo.buscar_por_nome("drogaria araújo") is not None
