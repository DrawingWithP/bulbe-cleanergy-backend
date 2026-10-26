"""
Dependencias do FastAPI. 'obter_usuario_atual' protege qualquer rota
que a declarar como parametro.
"""

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from app.domain.usuario import Usuario
from app.services.auth_service import auth_service
from app.services.usina_service import ErroDeNegocio

# tokenUrl faz o botao "Authorize" do Swagger saber onde fazer login.
# auto_error=False: nos mesmos tratamos a ausencia de token, no formato padrao.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/auth/login", auto_error=False)


def obter_usuario_atual(token: str | None = Depends(oauth2_scheme)) -> Usuario:
    if token is None:
        raise ErroDeNegocio(
            code="TOKEN_INVALIDO",
            message="Token ausente, invalido ou expirado.",
            status=401,
        )
    return auth_service.usuario_do_token(token)