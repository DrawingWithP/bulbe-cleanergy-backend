"""
Camada de Servico, AuthService: cadastro, login e validacao de token.
"""

import jwt

from app.core.security import (
    criar_token_acesso,
    decodificar_token,
    gerar_hash_senha,
    verificar_senha,
)
from app.domain.usuario import Token, Usuario, UsuarioCreate
from app.repositories.usuario_repository import UsuarioRepository, usuario_repository
from app.services.usina_service import ErroDeNegocio


class AuthService:
    def __init__(self, repository: UsuarioRepository) -> None:
        self._repository = repository

    def registrar(self, dados: UsuarioCreate) -> Usuario:
        if self._repository.buscar_por_email(dados.email) is not None:
            raise ErroDeNegocio(
                code="EMAIL_JA_CADASTRADO",
                message=f"Ja existe um usuario com o email {dados.email}.",
                status=409,
            )
        usuario = self._repository.criar(
            nome=dados.nome,
            email=dados.email,
            senha_hash=gerar_hash_senha(dados.senha),
        )
        return Usuario(**usuario.model_dump(exclude={"senha_hash"}))

    def autenticar(self, email: str, senha: str) -> Token:
        usuario = self._repository.buscar_por_email(email)
        # Mesma mensagem para email inexistente e senha errada:
        # assim a API nao revela quais emails estao cadastrados.
        if usuario is None or not verificar_senha(senha, usuario.senha_hash):
            raise ErroDeNegocio(
                code="CREDENCIAIS_INVALIDAS",
                message="Email ou senha incorretos.",
                status=401,
            )
        return Token(access_token=criar_token_acesso(usuario.email))

    def usuario_do_token(self, token: str) -> Usuario:
        try:
            email = decodificar_token(token)
        except jwt.PyJWTError:
            raise ErroDeNegocio(
                code="TOKEN_INVALIDO",
                message="Token ausente, invalido ou expirado.",
                status=401,
            )
        usuario = self._repository.buscar_por_email(email)
        if usuario is None:
            raise ErroDeNegocio(
                code="TOKEN_INVALIDO",
                message="Token ausente, invalido ou expirado.",
                status=401,
            )
        return Usuario(**usuario.model_dump(exclude={"senha_hash"}))


auth_service = AuthService(usuario_repository)
