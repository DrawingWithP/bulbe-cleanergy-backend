"""
Camada de Persistência, ParceiroRepository.

Contrato (Protocol) + InMemoryParceiroRepository (testes unitarios)
+ SqlParceiroRepository (API, parceiro_repository).
"""
from typing import Protocol

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.database import SessionLocal
from app.db.models import ParceiroModel
from app.domain.parceiro import Parceiro


class ParceiroRepository(Protocol):
    def listar(
        self,
        page: int = 1,
        limit: int = 20,
        categoria: str | None = None,
        ativo: bool | None = None,
    ) -> tuple[list[Parceiro], int]: ...
    def buscar_por_id(self, parceiro_id: str) -> Parceiro | None: ...
    def buscar_por_nome(self, nome: str) -> Parceiro | None: ...
    def criar(self, parceiro: Parceiro) -> Parceiro: ...
    def atualizar(self, parceiro: Parceiro) -> Parceiro: ...
    def remover(self, parceiro_id: str) -> bool: ...


class InMemoryParceiroRepository:
    def __init__(self) -> None:
        self._parceiros: dict[str, Parceiro] = {}
        self._inicializar_mock()

    def _inicializar_mock(self) -> None:
        p1 = Parceiro(
            id="1d2c3b4a-5e6f-4071-8293-a4b5c6d7e8f9",
            nome="Drogaria Araújo",
            categoria="Farmácia",
            logo_url="https://cdn.bulbeenergia.com.br/parceiros/araujo.png",
            ativo=True,
            criado_em="2026-05-20T12:00:00Z",
        )
        p2 = Parceiro(
            id="2b3c4d5e-6f70-4812-9a3b-c4d5e6f70819",
            nome="Banco Inter",
            categoria="Banco",
            logo_url="https://cdn.bulbeenergia.com.br/parceiros/inter.png",
            ativo=True,
            criado_em="2026-05-21T10:00:00Z",
        )
        self._parceiros[p1.id] = p1
        self._parceiros[p2.id] = p2

    def listar(
        self,
        page: int = 1,
        limit: int = 20,
        categoria: str | None = None,
        ativo: bool | None = None,
    ) -> tuple[list[Parceiro], int]:
        todos = list(self._parceiros.values())
        if categoria:
            todos = [p for p in todos if p.categoria.lower() == categoria.lower()]
        if ativo is not None:
            todos = [p for p in todos if p.ativo == ativo]

        total = len(todos)
        inicio = (page - 1) * limit
        fim = inicio + limit
        return todos[inicio:fim], total

    def buscar_por_id(self, parceiro_id: str) -> Parceiro | None:
        return self._parceiros.get(parceiro_id)

    def buscar_por_nome(self, nome: str) -> Parceiro | None:
        nome_limpo = nome.strip().lower()
        for p in self._parceiros.values():
            if p.nome.strip().lower() == nome_limpo:
                return p
        return None

    def criar(self, parceiro: Parceiro) -> Parceiro:
        self._parceiros[parceiro.id] = parceiro
        return parceiro

    def atualizar(self, parceiro: Parceiro) -> Parceiro:
        self._parceiros[parceiro.id] = parceiro
        return parceiro

    def remover(self, parceiro_id: str) -> bool:
        if parceiro_id in self._parceiros:
            del self._parceiros[parceiro_id]
            return True
        return False


class SqlParceiroRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def listar(
        self,
        page: int = 1,
        limit: int = 20,
        categoria: str | None = None,
        ativo: bool | None = None,
    ) -> tuple[list[Parceiro], int]:
        with self._session_factory() as session:
            consulta = select(ParceiroModel)
            if categoria:
                consulta = consulta.where(func.lower(ParceiroModel.categoria) == categoria.lower())
            if ativo is not None:
                consulta = consulta.where(ParceiroModel.ativo == ativo)
            total = session.scalar(select(func.count()).select_from(consulta.subquery()))
            modelos = session.scalars(
                consulta.order_by(ParceiroModel.criado_em, ParceiroModel.id)
                .offset((page - 1) * limit)
                .limit(limit)
            ).all()
            return [Parceiro.model_validate(m) for m in modelos], total or 0

    def buscar_por_id(self, parceiro_id: str) -> Parceiro | None:
        with self._session_factory() as session:
            modelo = session.get(ParceiroModel, parceiro_id)
            return Parceiro.model_validate(modelo) if modelo else None

    def buscar_por_nome(self, nome: str) -> Parceiro | None:
        # Comparacao sem diferenciar maiusculas feita no Python: o lower() do
        # SQLite nao entende acentos (ex.: "Araújo" x "ARAÚJO").
        nome_limpo = nome.strip().lower()
        with self._session_factory() as session:
            for modelo in session.scalars(select(ParceiroModel)).all():
                if modelo.nome.strip().lower() == nome_limpo:
                    return Parceiro.model_validate(modelo)
            return None

    def criar(self, parceiro: Parceiro) -> Parceiro:
        with self._session_factory() as session:
            modelo = ParceiroModel(**parceiro.model_dump(mode="json"))
            session.add(modelo)
            session.commit()
            session.refresh(modelo)
            return Parceiro.model_validate(modelo)

    def atualizar(self, parceiro: Parceiro) -> Parceiro:
        with self._session_factory() as session:
            modelo = session.get(ParceiroModel, parceiro.id)
            if modelo is None:
                modelo = ParceiroModel(id=parceiro.id)
                session.add(modelo)
            for campo, valor in parceiro.model_dump(mode="json").items():
                setattr(modelo, campo, valor)
            session.commit()
            session.refresh(modelo)
            return Parceiro.model_validate(modelo)

    def remover(self, parceiro_id: str) -> bool:
        with self._session_factory() as session:
            modelo = session.get(ParceiroModel, parceiro_id)
            if modelo is None:
                return False
            session.delete(modelo)
            session.commit()
            return True


parceiro_repository: ParceiroRepository = SqlParceiroRepository(SessionLocal)
