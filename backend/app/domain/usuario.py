"""
Camada de Dominio, entidade Usuario (operador do painel da Bulbe Energia).
"""

from pydantic import BaseModel, Field


class UsuarioCreate(BaseModel):
    """Dados enviados para cadastrar um usuario."""
    nome: str = Field(..., min_length=3, max_length=100)
    email: str = Field(..., pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", description="Email do usuario")
    senha: str = Field(..., min_length=8, max_length=72, description="Minimo de 8 caracteres")


class Usuario(BaseModel):
    """Representacao publica do usuario. Nunca expoe a senha."""
    id: int
    nome: str
    email: str


class UsuarioInterno(Usuario):
    """Usuario como fica guardado no repositorio, com o hash da senha."""
    senha_hash: str


class Token(BaseModel):
    """Resposta do login."""
    access_token: str
    token_type: str = "bearer"