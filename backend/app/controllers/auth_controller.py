"""
Camada de Apresentacao, AuthController.
"""

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.core.dependencies import obter_usuario_atual
from app.domain.usuario import Token, Usuario, UsuarioCreate
from app.services.auth_service import auth_service

router = APIRouter(prefix="/v1/auth", tags=["Autenticacao"])


@router.post("/registrar", response_model=Usuario, status_code=status.HTTP_201_CREATED)
def registrar(dados: UsuarioCreate) -> Usuario:
    """Cadastra um novo usuario do painel."""
    return auth_service.registrar(dados)


@router.post("/login", response_model=Token)
def login(form: OAuth2PasswordRequestForm = Depends()) -> Token:
    """
    Recebe username (o email) e password como formulario
    e devolve o token JWT.
    """
    return auth_service.autenticar(form.username, form.password)


@router.get("/me", response_model=Usuario)
def quem_sou_eu(usuario: Usuario = Depends(obter_usuario_atual)) -> Usuario:
    """Devolve o usuario dono do token enviado."""
    return usuario