"""
Camada de Repositorio para Indicacoes.

Contrato (Protocol) + InMemoryIndicacaoRepository (testes unitarios)
+ SqlIndicacaoRepository (API, indicacao_repository).
"""

from typing import Protocol

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.database import SessionLocal
from app.db.models import IndicacaoModel
from app.domain.indicacao import (
    Indicacao,
    IndicacaoCreate,
    StatusIndicacao,
)


BONUS_INDICACAO = 50.0


def _normalizar_contato(contato: str) -> str:
    """
    Normaliza o contato para comparacoes.
    """

    return contato.strip().lower()


class IndicacaoRepository(Protocol):
    def criar(
        self,
        dados: IndicacaoCreate,
    ) -> Indicacao:
        ...

    def buscar_por_id(
        self,
        indicacao_id: int,
    ) -> Indicacao | None:
        ...

    def listar_por_cliente(
        self,
        cliente_id: int,
    ) -> list[Indicacao]:
        ...

    def buscar_por_contato(
        self,
        contato: str,
    ) -> Indicacao | None:
        ...

    def excluir(
        self,
        indicacao_id: int,
    ) -> bool:
        ...


class InMemoryIndicacaoRepository:
    """
    Repositorio em memoria para indicacoes.
    """

    def __init__(self) -> None:
        self._indicacoes: dict[int, Indicacao] = {}
        self._proximo_id = 1

    def criar(
        self,
        dados: IndicacaoCreate,
    ) -> Indicacao:
        indicacao = Indicacao(
            id=self._proximo_id,
            cliente_id=dados.cliente_id,
            nome=dados.nome,
            contato=dados.contato.strip(),
            situacao=StatusIndicacao.pendente,
            bonus=BONUS_INDICACAO,
        )

        self._indicacoes[indicacao.id] = indicacao
        self._proximo_id += 1

        return indicacao

    def buscar_por_id(
        self,
        indicacao_id: int,
    ) -> Indicacao | None:
        return self._indicacoes.get(indicacao_id)

    def listar_por_cliente(
        self,
        cliente_id: int,
    ) -> list[Indicacao]:
        indicacoes = [
            indicacao
            for indicacao in self._indicacoes.values()
            if indicacao.cliente_id == cliente_id
        ]

        return sorted(
            indicacoes,
            key=lambda indicacao: indicacao.id,
        )

    def buscar_por_contato(
        self,
        contato: str,
    ) -> Indicacao | None:
        contato_normalizado = _normalizar_contato(
            contato
        )

        for indicacao in self._indicacoes.values():
            if (
                _normalizar_contato(indicacao.contato)
                == contato_normalizado
            ):
                return indicacao

        return None

    def excluir(
        self,
        indicacao_id: int,
    ) -> bool:
        if indicacao_id not in self._indicacoes:
            return False

        del self._indicacoes[indicacao_id]

        return True


class SqlIndicacaoRepository:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
    ) -> None:
        self._session_factory = session_factory

    def criar(
        self,
        dados: IndicacaoCreate,
    ) -> Indicacao:
        with self._session_factory() as session:
            modelo = IndicacaoModel(
                cliente_id=dados.cliente_id,
                nome=dados.nome,
                contato=dados.StatusIndicacao.pendente.value,
                bonus=BONUS_INDICACAO,
            )

            session.add(modelo)
            session.commit()
            session.refresh(modelo)

            return Indicacao.model_validate(modelo)

    def buscar_por_id(
        self,
        indicacao_id: int,
    ) -> Indicacao | None:
        with self._session_factory() as session:
            modelo = session.get(
                IndicacaoModel,
                indicacao_id,
            )

            if modelo is None:
                return None

            return Indicacao.model_validate(modelo)

    def listar_por_cliente(
        self,
        cliente_id: int,
    ) -> listwith self._session_factory() as session:
            consulta = (
                select(IndicacaoModel)
                .where(
                    IndicacaoModel.cliente_id
                    == cliente_id
                )
                .order_by(IndicacaoModel.id)
            )

            modelos = session.scalars(
                consulta
            ).all()

            return [
                Indicacao.model_validate(modelo)
                for modelo in modelos
            ]

    def buscar_por_contato(
        self,
        contato: str,
    ) -> Indicacao | None:
        contato_normalizado = _normalizar_contato(
            contato
        )

        with self._session_factory() as session:
            consulta = select(
                IndicacaoModel
            ).where(
                func.lower(
                    func.trim(IndicacaoModel.contato)
                )
                == contato_normalizado
            )

            modelo = session.scalars(
                consulta
            ).first()

            if modelo is None:
                return None

            return Indicacao.model_validate(modelo)

    def excluir(
        self,
        indicacao_id: int,
    ) -> bool:
        with self._session_factory() as session:
            modelo = session.get(
                IndicacaoModel,
                indicacao_id,
            )

            if modelo is None:
                return False

            session.delete(modelo)
            session.commit()

            return True


indicacao_repository: IndicacaoRepository = (
    SqlIndicacaoRepository(SessionLocal)
)
