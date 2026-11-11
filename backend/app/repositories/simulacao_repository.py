"""
Camada de Persistencia, SimulacaoRepository.

Contrato (Protocol) + InMemorySimulacaoRepository (testes unitarios)
+ SqlSimulacaoRepository (API, simulacao_repository).
"""

from datetime import date
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.db.database import SessionLocal
from app.db.models import SimulacaoModel
from app.domain.simulacao import (
    Simulacao,
    SimulacaoCreate,
)


class SimulacaoRepository(Protocol):
    def listar(self) -> list[Simulacao]:
        ...

    def buscar_por_id(
        self,
        simulacao_id: int,
    ) -> Simulacao | None:
        ...

    def criar(
        self,
        dados: SimulacaoCreate,
    ) -> Simulacao:
        ...

    def remover(
        self,
        simulacao_id: int,
    ) -> bool:
        ...


class InMemorySimulacaoRepository:
    def __init__(self) -> None:
        self._simulacoes: dict[int, Simulacao] = {}
        self._proximo_id = 1

    def listar(self) -> list[Simulacao]:
        return sorted(
            self._simulacoes.values(),
            key=lambda simulacao: simulacao.id,
        )

    def buscar_por_id(
        self,
        simulacao_id: int,
    ) -> Simulacao | None:
        return self._simulacoes.get(
            simulacao_id
        )

    def criar(
        self,
        dados: SimulacaoCreate,
    ) -> Simulacao:
        simulacao = Simulacao(
            id=self._proximo_id,
            data_ativacao=date.today(),
            **dados.model_dump(),
        )

        self._simulacoes[
            simulacao.id
        ] = simulacao

        self._proximo_id += 1

        return simulacao

    def remover(
        self,
        simulacao_id: int,
    ) -> bool:
        if simulacao_id not in self._simulacoes:
            return False

        del self._simulacoes[
            simulacao_id
        ]

        return True


class SqlSimulacaoRepository:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
    ) -> None:
        self._session_factory = session_factory

    def listar(self) -> list[Simulacao]:
        with self._session_factory() as session:
            consulta = select(
                SimulacaoModel
            ).order_by(
                SimulacaoModel.id
            )

            modelos = session.scalars(
                consulta
            ).all()

            return [
                Simulacao.model_validate(modelo)
                for modelo in modelos
            ]

    def buscar_por_id(
        self,
        simulacao_id: int,
    ) -> Simulacao | None:
        with self._session_factory() as session:
            modelo = session.get(
                SimulacaoModel,
                simulacao_id,
            )

            if modelo is None:
                return None

            return Simulacao.model_validate(
                modelo
            )

    def criar(
        self,
        dados: SimulacaoCreate,
    ) -> Simulacao:
        with self._session_factory() as session:
            modelo = SimulacaoModel(
                **dados.model_dump(mode="json"),
                data_ativacao=date.today(),
            )

            session.add(modelo)
            session.commit()
            session.refresh(modelo)

            return Simulacao.model_validate(
                modelo
            )

    def remover(
        self,
        simulacao_id: int,
    ) -> bool:
        with self._session_factory() as session:
            modelo = session.get(
                SimulacaoModel,
                simulacao_id,
            )

            if modelo is None:
                return False

            session.delete(modelo)
            session.commit()

            return True


# Uma unica instancia compartilhada por toda a aplicacao.
simulacao_repository: SimulacaoRepository = (
    SqlSimulacaoRepository(SessionLocal)
)
