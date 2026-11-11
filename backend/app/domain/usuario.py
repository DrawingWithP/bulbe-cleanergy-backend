"""
Camada de Dominio, entidade Usuario
(operador do painel da Bulbe Energia).
"""

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
)


class UsuarioCreate(BaseModel):
    """
    Dados enviados para cadastrar um usuario.
    """

    nome: str = Field(
        ...,
        min_length=3,
        max_length=100,
    )

    email: EmailStr = Field(
        ...,
        description="Email do usuario",
    )

    senha: str = Field(
        ...,
        min_length=8,
        max_length=72,
        description=(
            "Senha do usuario com minimo de 8 "
            "e maximo de 72 caracteres"
        ),
    )


class Usuario(BaseModel):
    """
    Representacao publica do usuario.
    Nunca expoe a senha ou seu hash.
    """

    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    nome: str
    email: EmailStr


class UsuarioInterno(Usuario):
    """
    Representacao interna do usuario,
    contendo o hash da senha.
    """

    senha_hash: str


class Token(BaseModel):
    """
    Resposta retornada após autenticacao.
    """

    access_token: str = Field(
        ...,
        min_length=1,
    )

    token_type: str = "bearer"
