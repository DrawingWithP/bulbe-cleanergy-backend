"""
Camada de Apresentacao, AuthController.
"""

from fastapi import (
    APIRouter,
    Depends,
    status,
)
from fastapi.security import OAuth2PasswordRequestForm

from app.core.dependencies import obter_usuario_atual
from app.domain.usuario import (
    Token,
    Usuario,
    UsuarioCreate,
)
from app.services.auth_service import auth_service


router = APIRouter(
    prefix="/v1/auth",
    tags=["Autenticacao"],
)


@router.post(
    "/registrar",
    response_model=Usuario,
    status_code=status.HTTP_201_CREATED,
)
def registrar(
    dados: UsuarioCreate,
) -> Usuario:
    """
    Cadastra um novo usuario do painel.
    """

    return auth_service.registrar(dados)


@router.post(
    "/login",
    response_model=Token,
    status_code=status.HTTP_200_OK,
)
def login(
    form: OAuth2PasswordRequestForm = Depends(),
) -> Token:
    """
    Realiza a autenticacao do usuario.

    O campo username do OAuth2 representa
    o email do usuario e password representa
    a senha.

    Retorna um token JWT em caso de sucesso.
    """

    return auth_service.autenticar(
        form.username,
        form.password,
    )


@router.get(
    "/me",
    response_model=Usuario,
    status_code=status.HTTP_200_OK,
)
def quem_sou_eu(
    usuario: Usuario = Depends(
        obter_usuario_atual
    ),
) -> Usuario:
    """
    Retorna os dados do usuario autenticado
    a partir do token JWT enviado.

    Requer autenticacao.
    """

    return usuario
