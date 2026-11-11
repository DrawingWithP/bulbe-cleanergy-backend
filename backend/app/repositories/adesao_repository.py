"""
Camada de Persistencia, AdesaoRepository.

Contrato (Protocol) + InMemoryAdesaoRepository (testes unitarios)
+ SqlAdesaoRepository (API, adesao_repository).
"""

from datetime import date
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.db.database import SessionLocal
from app.db.models import AdesaoModel
from app.domain.adesao import (
    Adesao,
    AdesaoCreate,
    AdesaoUpdate,
)


class AdesaoRepository(Protocol):
    """
    Contrato de persistencia para adesoes.
    """

    def listar(self) -> list[Adesao]:
        ...

    def buscar_por_id(
        self,
        adesao_id: int,
    ) -> Adesao | None:
        ...

    def criar(
        self,
        dados: AdesaoCreate,
    ) -> Adesao:
        ...

    def atualizar(
        self,
        adesao_id: int,
        dados: AdesaoUpdate,
    ) -> Adesao | None:
        ...

    def remover(
        self,
        adesao_id: int,
    ) -> bool:
        ...


class InMemoryAdesaoRepository:
    """
    Implementacao em memoria utilizada principalmente
    em testes unitarios.
    """

    def __init__(self) -> None:
        self._adesoes: dict[int, Adesao] = {}
        self._proximo_id = 1

    def listar(self) -> list[Adesao]:
        return list(
            self._adesoes.values()
        )

    def buscar_por_id(
        self,
        adesao_id: int,
    ) -> Adesao | None:
        return self._adesoes.get(
            adesao_id
        )

    def criar(
        self,
        dados: AdesaoCreate,
    ) -> Adesao:
        adesao = Adesao(
            id=self._proximo_id,
            data_ativacao=date.today(),
            **dados.model_dump(),
        )

        self._adesoes[
            adesao.id
        ] = adesao

        self._proximo_id += 1

        return adesao

    def atualizar(
        self,
        adesao_id: int,
        dados: AdesaoUpdate,
    ) -> Adesao | None:
        adesao_atual = self._adesoes.get(
            adesao_id
        )

        if adesao_atual is None:
            return None

        dados_atualizados = (
            adesao_atual.model_dump()
        )

        dados_atualizados.update(
            dados.model_dump(
                exclude_unset=True
            )
        )

        adesao_atualizada = Adesao(
            **dados_atualizados
        )

        self._adesoes[
            adesao_id
        ] = adesao_atualizada

        return adesao_atualizada

    def remover(
        self,
        adesao_id: int,
    ) -> bool:
        if adesao_id not in self._adesoes:
            return False

        del self._adesoes[
            adesao_id
        ]

        return True


class SqlAdesaoRepository:
    """
    Implementacao do repository utilizando SQLAlchemy.
    """

    def __init__(
        self,
        session_factory: sessionmaker[Session],
    ) -> None:
        self._session_factory = session_factory

    def listar(self) -> list[Adesao]:
        with self._session_factory() as session:
            consulta = select(
                AdesaoModel
            ).order_by(
                AdesaoModel.id
            )

            modelos = session.scalars(
                consulta
            ).all()

            return [
                Adesao.model_validate(modelo)
                for modelo in modelos
            ]

    def buscar_por_id(
        self,
        adesao_id: int,
    ) -> Adesao | None:
        with self._session_factory() as session:
            modelo = session.get(
                AdesaoModel,
                adesao_id,
            )

            if modelo is None:
                return None

            return Adesao.model_validate(
                modelo
            )

    def criar(
        self,
        dados: AdesaoCreate,
    ) -> Adesao:
        with self._session_factory() as session:
            modelo = AdesaoModel(
                **dados.model_dump(
                    mode="json"
                ),
                data_ativacao=date.today(),
            )

            session.add(modelo)
            session.commit()
            el_validate(
                modelo
            )

    def atualizar(
        self,
        adesao_id: int,
        dados: AdesaoUpdate,
    ) -> Adesao | None:
        with self._session_factory() as session:
            modelo = session.get(
                AdesaoModel,
                adesao_id,
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

            return Adesao.model_validate(
                modelo
            )

    def remover(
        self,
        adesao_id: int,
    ) -> bool:
        with self._session_factory() as session:
            modelo = session.get(
                AdesaoModel,
                adesao_id,
            )

            if modelo is None:
                return False

            session.delete(modelo)
            session.commit()

            return True


# Uma unica instancia compartilhada por toda a aplicacao.
adesao_repository: AdesaoRepository = (
    SqlAdesaoRepository(SessionLocal)
)
