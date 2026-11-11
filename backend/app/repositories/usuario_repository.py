"""
Camada de Persistencia, UsuarioRepository.

Contrato (Protocol) + InMemoryUsuarioRepository (testes unitarios)
+ SqlUsuarioRepository (API, usuario_repository).
"""

from typing import Protocol

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.database import SessionLocal
from app.db.models import UsuarioModel
from app.domain.usuario import UsuarioInterno


def _normalizar_email(email: str) -> str:
    return email.strip().lower()


class UsuarioRepository(Protocol):
    def buscar_por_email(
        self,
        email: str,
    ) -> UsuarioInterno | None:
        ...

    def criar(
        self,
        nome: str,
        email: str,
        senha_hash: str,
    ) -> UsuarioInterno:
        ...


class InMemoryUsuarioRepository:
    def __init__(self) -> None:
        self._usuarios: dict[str, UsuarioInterno] = {}
        self._proximo_id = 1

    def buscar_por_email(
        self,
        email: str,
    ) -> UsuarioInterno | None:
        email_normalizado = _normalizar_email(email)

        return self._usuarios.get(
            email_normalizado
        )

    def criar(
        self,
        nome: str,
        email: str,
        senha_hash: str,
    ) -> UsuarioInterno:
        email_normalizado = _normalizar_email(email)

        usuario = UsuarioInterno(
            id=self._proximo_id,
            nome=nome,
            email=email_normalizado,
            senha_hash=senha_hash,
        )

        self._usuarios[
            usuario.email
        ] = usuario

        self._proximo_id += 1

        return usuario


class SqlUsuarioRepository:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
    ) -> None:
        self._session_factory = session_factory

    @staticmethod
    def _para_dominio(
        modelo: UsuarioModel,
    ) -> UsuarioInterno:
        return UsuarioInterno(
            id=modelo.id,
            nome=modelo.nome,
            email=modelo.email,
            senha_hash=modelo.senha_hash,
        )

    def buscar_por_email(
        self,
        email: str,
    ) -> UsuarioInterno | None:
        email_normalizado = _normalizar_email(email)

        with self._session_factory() as session:
            consulta = select(
                UsuarioModel
            ).where(
                func.lower(UsuarioModel.email)
                == email_normalizado
            )

            modelo = session.scalars(
                consulta
            ).first()

            if modelo is None:
                return None

            return self._para_dominio(modelo)

    def criar(
        self,
        nome: str,
        email: str,
        senha_hash: str,
    ) -> UsuarioInterno:
        email_normalizado = _normalizar_email(email)

        with self._session_factory() as session:
            modelo = UsuarioModel(
                nome=nome,
                email=email_normalizado,
                senha_hash=senha_hash,
            )

            session.add(modelo)
            session.commit()
            session.refresh(modelo)

            return self._para_dominio(modelo)


usuario_repository: UsuarioRepository = (
    SqlUsuarioRepository(SessionLocal)
)
