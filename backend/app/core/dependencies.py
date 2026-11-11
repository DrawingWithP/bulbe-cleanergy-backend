"""
Dependencias do FastAPI.

'obter_usuario_atual' protege qualquer rota
que a declarar como parametro.
"""

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from app.domain.usuario import Usuario
from app.services.auth_service import auth_service
from app.services.usina_service import ErroDeNegocio


# tokenUrl informa ao botao "Authorize" do Swagger
# qual endpoint deve ser utilizado para autenticacao.
#
# auto_error=False permite tratar manualmente a ausencia
# do token utilizando o formato padrao de erro da aplicacao.
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/v1/auth/login",
    auto_error=False,
)


def obter_usuario_atual(
    token: str | None = Depends(oauth2_scheme),
) -> Usuario:
    """
    Retorna o usuario autenticado a partir do token JWT.

    Levanta ErroDeNegocio com status 401 caso o token
    esteja ausente, invalido ou expirado.
    """

    if token is None:
        raise ErroDeNegocio(
            code="TOKEN_INVALIDO",
            message="Token ausente, invalido ou expirado.",
            status=401,
        )

    return auth_service.usuario_do_token(token)
