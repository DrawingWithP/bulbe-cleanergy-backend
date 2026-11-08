"""
Camada de Persistencia, UsuarioRepository.

Contrato (Protocol) + InMemoryUsuarioRepository (testes unitarios)
+ SqlUsuarioRepository (API, usuario_repository).
"""
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.db.database import SessionLocal
from app.db.models import UsuarioModel
from app.domain.usuario import UsuarioInterno


class UsuarioRepository(Protocol):
    def buscar_por_email(self, email: str) -> UsuarioInterno | None: ...
    def criar(self, nome: str, email: str, senha_hash: str) -> UsuarioInterno: ...


class InMemoryUsuarioRepository:
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


class SqlUsuarioRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    @staticmethod
    def _para_dominio(modelo: UsuarioModel) -> UsuarioInterno:
        return UsuarioInterno(
            id=modelo.id,
            nome=modelo.nome,
            email=modelo.email,
            senha_hash=modelo.senha_hash,
        )

    def buscar_por_email(self, email: str) -> UsuarioInterno | None:
        with self._session_factory() as session:
            modelo = session.scalars(
                select(UsuarioModel).where(UsuarioModel.email == email.lower())
            ).first()
            return self._para_dominio(modelo) if modelo else None

    def criar(self, nome: str, email: str, senha_hash: str) -> UsuarioInterno:
        with self._session_factory() as session:
            modelo = UsuarioModel(nome=nome, email=email.lower(), senha_hash=senha_hash)
            session.add(modelo)
            session.commit()
            session.refresh(modelo)
            return self._para_dominio(modelo)


usuario_repository: UsuarioRepository = SqlUsuarioRepository(SessionLocal)
