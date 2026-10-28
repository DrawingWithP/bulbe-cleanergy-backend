"""
Testes unitários do AuthService: cadastro, login e validação de token.
"""
from datetime import timedelta

import pytest

from app.core.security import criar_token_acesso, verificar_senha
from app.domain.usuario import UsuarioCreate
from app.repositories.usuario_repository import UsuarioRepository
from app.services.auth_service import AuthService
from app.services.usina_service import ErroDeNegocio


@pytest.fixture
def repository() -> UsuarioRepository:
    return UsuarioRepository()


@pytest.fixture
def service(repository: UsuarioRepository) -> AuthService:
    return AuthService(repository)


@pytest.fixture
def dados_usuario() -> UsuarioCreate:
    return UsuarioCreate(nome="Operadora Bulbe", email="operacao@bulbe.com.br", senha="solar12345")


def test_registrar_usuario_com_sucesso(service: AuthService, dados_usuario: UsuarioCreate):
    """Cadastra o usuário e devolve os dados públicos, sem a senha."""
    usuario = service.registrar(dados_usuario)
    assert usuario.id == 1
    assert usuario.email == "operacao@bulbe.com.br"
    assert not hasattr(usuario, "senha_hash")


def test_registrar_guarda_somente_o_hash_da_senha(
    service: AuthService, repository: UsuarioRepository, dados_usuario: UsuarioCreate
):
    service.registrar(dados_usuario)
    salvo = repository.buscar_por_email("operacao@bulbe.com.br")
    assert salvo.senha_hash != "solar12345"
    assert verificar_senha("solar12345", salvo.senha_hash)


def test_registrar_email_duplicado(service: AuthService, dados_usuario: UsuarioCreate):
    """Um segundo cadastro com o mesmo email retorna 409."""
    service.registrar(dados_usuario)
    with pytest.raises(ErroDeNegocio) as erro:
        service.registrar(dados_usuario)
    assert erro.value.status == 409
    assert erro.value.code == "EMAIL_JA_CADASTRADO"


def test_registrar_email_duplicado_com_maiusculas(service: AuthService, dados_usuario: UsuarioCreate):
    """O email é guardado em minúsculas, então 'OPERACAO@...' conta como duplicado."""
    service.registrar(dados_usuario)
    dados_maiusculos = dados_usuario.model_copy(update={"email": "OPERACAO@BULBE.COM.BR"})
    with pytest.raises(ErroDeNegocio) as erro:
        service.registrar(dados_maiusculos)
    assert erro.value.status == 409


def test_autenticar_com_sucesso(service: AuthService, dados_usuario: UsuarioCreate):
    service.registrar(dados_usuario)
    token = service.autenticar("operacao@bulbe.com.br", "solar12345")
    assert token.access_token
    assert token.token_type == "bearer"


def test_autenticar_senha_incorreta(service: AuthService, dados_usuario: UsuarioCreate):
    service.registrar(dados_usuario)
    with pytest.raises(ErroDeNegocio) as erro:
        service.autenticar("operacao@bulbe.com.br", "senha-errada")
    assert erro.value.status == 401
    assert erro.value.code == "CREDENCIAIS_INVALIDAS"


def test_autenticar_email_inexistente_tem_mesma_mensagem(service: AuthService, dados_usuario: UsuarioCreate):
    """Email inexistente e senha errada devolvem a mesma mensagem, para não revelar quais emails existem."""
    service.registrar(dados_usuario)

    with pytest.raises(ErroDeNegocio) as erro_senha:
        service.autenticar("operacao@bulbe.com.br", "senha-errada")
    with pytest.raises(ErroDeNegocio) as erro_email:
        service.autenticar("ninguem@bulbe.com.br", "solar12345")

    assert erro_email.value.status == 401
    assert erro_email.value.code == erro_senha.value.code
    assert erro_email.value.message == erro_senha.value.message


def test_usuario_do_token_valido(service: AuthService, dados_usuario: UsuarioCreate):
    service.registrar(dados_usuario)
    token = service.autenticar("operacao@bulbe.com.br", "solar12345")
    usuario = service.usuario_do_token(token.access_token)
    assert usuario.email == "operacao@bulbe.com.br"
    assert usuario.nome == "Operadora Bulbe"


def test_usuario_do_token_invalido(service: AuthService):
    with pytest.raises(ErroDeNegocio) as erro:
        service.usuario_do_token("token-invalido")
    assert erro.value.status == 401
    assert erro.value.code == "TOKEN_INVALIDO"


def test_usuario_do_token_expirado(service: AuthService, dados_usuario: UsuarioCreate):
    service.registrar(dados_usuario)
    token_expirado = criar_token_acesso("operacao@bulbe.com.br", expira_em=timedelta(minutes=-1))
    with pytest.raises(ErroDeNegocio) as erro:
        service.usuario_do_token(token_expirado)
    assert erro.value.status == 401
    assert erro.value.code == "TOKEN_INVALIDO"


def test_usuario_do_token_de_usuario_inexistente(service: AuthService):
    """Token com assinatura válida, mas de um email que não está cadastrado, retorna 401."""
    token = criar_token_acesso("fantasma@bulbe.com.br")
    with pytest.raises(ErroDeNegocio) as erro:
        service.usuario_do_token(token)
    assert erro.value.status == 401
    assert erro.value.code == "TOKEN_INVALIDO"
