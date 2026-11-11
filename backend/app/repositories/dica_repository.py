"""
Camada de Persistencia, DicaRepository.

Contrato (Protocol) + InMemoryDicaRepository (testes unitarios)
+ SqlDicaRepository (API, dica_repository).
"""

from datetime import date
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.db.database import SessionLocal
from app.db.models import DicaModel
from app.domain.dica import (
    Dica,
    DicaCreate,
    DicaUpdate,
)


class DicaRepository(Protocol):
    def listar(self) -> list[Dica]:
        ...

    def buscar_por_id(
        self,
        dica_id: int,
    ) -> Dica | None:
        ...

    def criar(
        self,
        dados: DicaCreate,
    ) -> Dica:
        ...

    def atualizar(
        self,
        dica_id: int,
        dados: DicaUpdate,
    ) -> Dica | None:
        ...

    def remover(
        self,
        dica_id: int,
    ) -> bool:
        ...


class InMemoryDicaRepository:
    def __init__(self) -> None:
        self._dicas: dict[int, Dica] = {}
        self._proximo_id = 1

    def listar(self) -> list[Dica]:
        return sorted(
            self._dicas.values(),
            key=lambda dica: dica.id,
        )

    def buscar_por_id(
        self,
        dica_id: int,
    ) -> Dica | None:
        return self._dicas.get(dica_id)

    def criar(
        self,
        dados: DicaCreate,
    ) -> Dica:
        dica = Dica(
            id=self._proximo_id,
            data_ativacao=date.today(),
            **dados.model_dump(),
        )

        self._dicas[dica.id] = dica
        self._proximo_id += 1

        return dica

    def atualizar(
        self,
        dica_id: int,
        dados: DicaUpdate,
    ) -> Dica | None:
        dica_atual = self._dicas.get(dica_id)

        if dica_atual is None:
            return None

        dados_atualizados = dica_atual.model_dump()

        dados_atualizados.update(
            dados.model_dump(
                exclude_unset=True,
            )
        )

        dica_atualizada = Dica(
            **dados_atualizados
        )

        self._dicas[dica_id] = dica_atualizada

        return dica_atualizada

    def remover(
        self,
        dica_id: int,
    ) -> bool:
        if dica_id not in self._dicas:
            return False

        del self._dicas[dica_id]

        return True


class SqlDicaRepository:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
    ) -> None:
        self._session_factory = session_factory

    def listar(self) -> list[Dica]:
        with self._session_factory() as session:
            consulta = select(
                DicaModel
            ).order_by(
                DicaModel.id
            )

            modelos = session.scalars(
                consulta
            ).all()

            return [
                Dica.model_validate(modelo)
                for modelo in modelos
            ]

    def buscar_por_id(
        self,
        dica_id: int,
    ) -> Dica | None:
        with self._session_factory() as session:
            modelo = session.get(
                DicaModel,
                dica_id,
            )

            if modelo is None:
                return None

            return Dica.model_validate(modelo)

    def criar(
        self,
        dados: DicaCreate,
    ) -> Dica:
        with self._session_factory() as session:
            modelo = DicaModel(
                **dados.model_dump(mode="json"),
                data_ativacao=date.today(),
            )

            session.add(modelo)
            session.commit()
            session.refresh(modelo)

            return Dica.model_validate(modelo)

    def atualizar(
        self,
        dica_id: int,
        dados: DicaUpdate,
    ) -> Dica | None:
        with self._session_factory() as session:
            modelo = session.get(
                DicaModel,
                dica_id,
            )

            if modelo is None:
                return None

            dados_atualizados = dados.model_dump(
                mode="json",
                exclude_unset=True,
            )

            for campo, valor in dados_atualizados.items():
                setattr(
                    modelo,
                    campo,
                    valor,
                )

            session.commit()
            session.refresh(modelo)

            return Dica.model_validate(modelo)

    def remover(
        self,
        dica_id: int,
    ) -> bool:
        with self._session_factory() as session:
            modelo = session.get(
                DicaModel,
                dica_id,
            )

            if modelo is None:
                return False

            session.delete(modelo)
            session.commit()

            return True


dica_repository: DicaRepository = (
    SqlDicaRepository(SessionLocal)
)
