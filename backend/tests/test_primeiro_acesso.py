"""
Testes unitários para o módulo de Primeiro Acesso (US-09 e US-10).
"""
from datetime import datetime, timedelta, timezone
import pytest

from app.domain.primeiro_acesso import (
    CanalVerificacao,
    ConfirmacaoRequest,
    SituacaoVerificacao,
    VerificacaoRequest,
)
from app.repositories.primeiro_acesso_repository import PrimeiroAcessoRepository
from app.services.primeiro_acesso_service import ErroDeNegocio, PrimeiroAcessoService


@pytest.fixture
def repository() -> PrimeiroAcessoRepository:
    return PrimeiroAcessoRepository()


@pytest.fixture
def service(repository: PrimeiroAcessoRepository) -> PrimeiroAcessoService:
    return PrimeiroAcessoService(repository)


def test_solicitar_verificacao_com_sucesso(service: PrimeiroAcessoService):
    """US-09: Cliente existente solicita código e recebe status 202 com destino mascarado."""
    requisicao = VerificacaoRequest(cpf="123.456.789-00", canal=CanalVerificacao.whatsapp)
    resposta = service.solicitar_verificacao(requisicao)

    assert resposta.verificacao_id is not None
    assert resposta.canal == "whatsapp"
    assert resposta.destino_mascarado == "(31) *****-1234"
    assert resposta.expira_em is not None


def test_solicitar_verificacao_cpf_invalido(service: PrimeiroAcessoService):
    """US-09: Rejeita CPF com tamanho ou formato inválido com erro 400."""
    with pytest.raises(ErroDeNegocio) as erro:
        service.solicitar_verificacao(VerificacaoRequest(cpf="12345"))
    assert erro.value.status == 400
    assert erro.value.code == "CPF_INVALIDO"

    with pytest.raises(ErroDeNegocio) as erro_digitos_iguais:
        service.solicitar_verificacao(VerificacaoRequest(cpf="11111111111"))
    assert erro_digitos_iguais.value.status == 400
    assert erro_digitos_iguais.value.code == "CPF_INVALIDO"


def test_solicitar_verificacao_cpf_nao_cadastrado(service: PrimeiroAcessoService):
    """US-09: Retorna 404 se o CPF informado não corresponder a um cliente Bulbe."""
    requisicao = VerificacaoRequest(cpf="999.888.777-66", canal=CanalVerificacao.sms)
    with pytest.raises(ErroDeNegocio) as erro:
        service.solicitar_verificacao(requisicao)
    assert erro.value.status == 404
    assert erro.value.code == "CLIENTE_NAO_ENCONTRADO"


def test_confirmar_codigo_com_sucesso(service: PrimeiroAcessoService, repository: PrimeiroAcessoRepository):
    """US-10: Confirma código gerado, habilitando acesso ao app com status 201."""
    # 1. Solicita verificação
    verif = service.solicitar_verificacao(VerificacaoRequest(cpf="12345678900", canal=CanalVerificacao.whatsapp))

    # 2. Obtém o código gerado no repositório
    verificacao_salva = repository.buscar_verificacao_por_id(verif.verificacao_id)
    assert verificacao_salva is not None
    codigo_gerado = verificacao_salva.codigo

    # 3. Confirma o código
    confirmacao = service.confirmar_codigo(
        ConfirmacaoRequest(verificacao_id=verif.verificacao_id, codigo=codigo_gerado)
    )

    assert confirmacao.cliente_id == "8f1c2a6e-4b7d-4c1a-9f52-3d6a1b0c7e11"
    assert confirmacao.acesso_habilitado is True
    assert confirmacao.confirmado_em is not None


def test_confirmar_codigo_incorreto(service: PrimeiroAcessoService, repository: PrimeiroAcessoRepository):
    """US-10: Código incorreto retorna 400 e incrementa tentativas."""
    verif = service.solicitar_verificacao(VerificacaoRequest(cpf="12345678900"))

    with pytest.raises(ErroDeNegocio) as erro:
        service.confirmar_codigo(ConfirmacaoRequest(verificacao_id=verif.verificacao_id, codigo="000000"))
    assert erro.value.status == 400
    assert erro.value.code == "CODIGO_INVALIDO"

    verificacao_salva = repository.buscar_verificacao_por_id(verif.verificacao_id)
    assert verificacao_salva.tentativas == 1


def test_confirmar_codigo_expirado(service: PrimeiroAcessoService, repository: PrimeiroAcessoRepository):
    """US-10: Código expirado retorna 410 Gone."""
    verif = service.solicitar_verificacao(VerificacaoRequest(cpf="12345678900"))

    # Força a data de expiração para o passado
    verificacao_salva = repository.buscar_verificacao_por_id(verif.verificacao_id)
    verificacao_salva.expira_em = datetime.now(timezone.utc) - timedelta(minutes=5)
    repository.atualizar_verificacao(verificacao_salva)

    with pytest.raises(ErroDeNegocio) as erro:
        service.confirmar_codigo(
            ConfirmacaoRequest(verificacao_id=verif.verificacao_id, codigo=verificacao_salva.codigo)
        )
    assert erro.value.status == 410
    assert erro.value.code == "CODIGO_EXPIRADO"


def test_confirmar_codigo_ja_utilizado(service: PrimeiroAcessoService, repository: PrimeiroAcessoRepository):
    """US-10: Reutilização de código já usado retorna 400."""
    verif = service.solicitar_verificacao(VerificacaoRequest(cpf="12345678900"))
    verificacao_salva = repository.buscar_verificacao_por_id(verif.verificacao_id)

    # Primeira confirmação válida
    service.confirmar_codigo(ConfirmacaoRequest(verificacao_id=verif.verificacao_id, codigo=verificacao_salva.codigo))

    # Segunda tentativa com o mesmo id
    with pytest.raises(ErroDeNegocio) as erro:
        service.confirmar_codigo(
            ConfirmacaoRequest(verificacao_id=verif.verificacao_id, codigo=verificacao_salva.codigo)
        )
    assert erro.value.status == 400
    assert erro.value.code == "CODIGO_JA_UTILIZADO"


def test_confirmar_verificacao_inexistente(service: PrimeiroAcessoService):
    """US-10: ID de verificação que não existe no sistema retorna 404."""
    with pytest.raises(ErroDeNegocio) as erro:
        service.confirmar_codigo(ConfirmacaoRequest(verificacao_id="id-inexistente", codigo="123456"))
    assert erro.value.status == 404
    assert erro.value.code == "RECURSO_NAO_ENCONTRADO"


def test_canal_padrao_e_whatsapp(service: PrimeiroAcessoService):
    resposta = service.solicitar_verificacao(VerificacaoRequest(cpf="12345678900"))
    assert resposta.canal == "whatsapp"


def test_codigo_gerado_tem_6_digitos_e_expira_em_15_minutos(
    service: PrimeiroAcessoService, repository: PrimeiroAcessoRepository
):
    verif = service.solicitar_verificacao(VerificacaoRequest(cpf="12345678900"))
    salva = repository.buscar_verificacao_por_id(verif.verificacao_id)

    assert salva.codigo.isdigit() and len(salva.codigo) == 6
    assert salva.expira_em - salva.criado_em == timedelta(minutes=15)
    assert salva.situacao == SituacaoVerificacao.pendente


def test_destino_mascarado_com_telefone_incompleto(
    service: PrimeiroAcessoService, repository: PrimeiroAcessoRepository
):
    """Telefone com menos de 10 dígitos é totalmente mascarado."""
    repository.adicionar_cliente_mock(
        {"id": "cliente-x", "cpf": "55566677788", "telefone": "1234", "acesso_habilitado": False}
    )
    resposta = service.solicitar_verificacao(VerificacaoRequest(cpf="55566677788"))
    assert resposta.destino_mascarado == "(**) *****-****"


def test_cada_solicitacao_gera_uma_verificacao_nova(service: PrimeiroAcessoService):
    primeira = service.solicitar_verificacao(VerificacaoRequest(cpf="12345678900"))
    segunda = service.solicitar_verificacao(VerificacaoRequest(cpf="12345678900"))
    assert primeira.verificacao_id != segunda.verificacao_id


def test_confirmar_codigo_habilita_acesso_do_cliente(
    service: PrimeiroAcessoService, repository: PrimeiroAcessoRepository
):
    """US-10: Depois da confirmação, o cliente fica com acesso habilitado."""
    verif = service.solicitar_verificacao(VerificacaoRequest(cpf="98765432100"))
    codigo = repository.buscar_verificacao_por_id(verif.verificacao_id).codigo

    service.confirmar_codigo(ConfirmacaoRequest(verificacao_id=verif.verificacao_id, codigo=codigo))

    assert repository.buscar_cliente_por_cpf("98765432100")["acesso_habilitado"] is True
    assert repository.buscar_cliente_por_cpf("12345678900")["acesso_habilitado"] is False


def test_confirmar_codigo_aceita_espacos_em_volta(
    service: PrimeiroAcessoService, repository: PrimeiroAcessoRepository
):
    verif = service.solicitar_verificacao(VerificacaoRequest(cpf="12345678900"))
    codigo = repository.buscar_verificacao_por_id(verif.verificacao_id).codigo

    confirmacao = service.confirmar_codigo(
        ConfirmacaoRequest(verificacao_id=verif.verificacao_id, codigo=f" {codigo} ")
    )
    assert confirmacao.acesso_habilitado is True


def test_codigo_expirado_marca_verificacao_como_expirada(
    service: PrimeiroAcessoService, repository: PrimeiroAcessoRepository
):
    verif = service.solicitar_verificacao(VerificacaoRequest(cpf="12345678900"))
    salva = repository.buscar_verificacao_por_id(verif.verificacao_id)
    salva.expira_em = datetime.now(timezone.utc) - timedelta(seconds=1)

    with pytest.raises(ErroDeNegocio):
        service.confirmar_codigo(ConfirmacaoRequest(verificacao_id=salva.id, codigo=salva.codigo))

    assert repository.buscar_verificacao_por_id(salva.id).situacao == SituacaoVerificacao.expirada


def test_codigo_correto_funciona_depois_de_tentativas_erradas(
    service: PrimeiroAcessoService, repository: PrimeiroAcessoRepository
):
    verif = service.solicitar_verificacao(VerificacaoRequest(cpf="12345678900"))
    salva = repository.buscar_verificacao_por_id(verif.verificacao_id)

    for _ in range(3):
        with pytest.raises(ErroDeNegocio):
            service.confirmar_codigo(ConfirmacaoRequest(verificacao_id=salva.id, codigo="000000"))

    assert salva.tentativas == 3
    assert service.confirmar_codigo(
        ConfirmacaoRequest(verificacao_id=salva.id, codigo=salva.codigo)
    ).acesso_habilitado is True
