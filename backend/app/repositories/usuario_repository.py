"""
Camada de Persistencia, UsuarioRepository (em memoria, como o de Usinas).
"""

from app.domain.usuario import UsuarioInterno


class UsuarioRepository:
    def __init__(self) -> None:
        self._usuarios: dict[str, UsuarioInterno] = {}
        self._proximo_id: int = 1

    def buscar_por_email(self, email: str) -> UsuarioInterno | None:
        return self._usuarios.get(email.lower())

    def criar(self, nome: str, email: str, senha_hash: str) -> UsuarioInterno:
        usuario = UsuarioInterno(
            id=self._proximo_id,
            nome=nome,
            email=email.lower(),
            senha_hash=senha_hash,
        )
        self._usuarios[usuario.email] = usuario
        self._proximo_id += 1
        return usuario


usuario_repository = UsuarioRepository()