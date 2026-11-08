"""
Camada de Repositorio para Indicacoes.

Contrato (Protocol) + InMemoryIndicacaoRepository (testes unitarios)
+ SqlIndicacaoRepository (API, indicacao_repository).
"""
from typing import List, Optional, Protocol

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.database import SessionLocal
from app.db.models import IndicacaoModel
from app.domain.indicacao import Indicacao, IndicacaoCreate, StatusIndicacao


class IndicacaoRepository(Protocol):
    def criar(self, dados: IndicacaoCreate) -> Indicacao: ...
    def buscar_por_id(self, indicacao_id: int) -> Optional[Indicacao]: ...
    def listar_por_cliente(self, cliente_id: int) -> List[Indicacao]: ...
    def buscar_por_contato(self, contato: str) -> Optional[Indicacao]: ...
    def excluir(self, indicacao_id: int) -> bool: ...


class InMemoryIndicacaoRepository:
    """Repositorio em memoria para indicacoes."""

    def __init__(self):
        self._indicacoes: List[Indicacao] = []
        self._next_id = 1

    def criar(self, dados: IndicacaoCreate) -> Indicacao:
        indicacao = Indicacao(
            id=self._next_id,
            cliente_id=dados.cliente_id,
            nome=dados.nome,
            contato=dados.contato,
            situacao=StatusIndicacao.pendente,
            bonus=50.0
        )

        self._indicacoes.append(indicacao)
        self._next_id += 1

        return indicacao

    def buscar_por_id(self, indicacao_id: int) -> Optional[Indicacao]:
        for indicacao in self._indicacoes:
            if indicacao.id == indicacao_id:
                return indicacao

        return None

    def listar_por_cliente(self, cliente_id: int) -> List[Indicacao]:
        return [
            indicacao
            for indicacao in self._indicacoes
            if indicacao.cliente_id == cliente_id
        ]

    def buscar_por_contato(self, contato: str) -> Optional[Indicacao]:
        for indicacao in self._indicacoes:
            if indicacao.contato.lower() == contato.lower():
                return indicacao

        return None

    def excluir(self, indicacao_id: int) -> bool:
        indicacao = self.buscar_por_id(indicacao_id)

        if indicacao is None:
            return False

        self._indicacoes.remove(indicacao)
        return True


class SqlIndicacaoRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def criar(self, dados: IndicacaoCreate) -> Indicacao:
        with self._session_factory() as session:
            modelo = IndicacaoModel(
                cliente_id=dados.cliente_id,
                nome=dados.nome,
                contato=dados.contato,
                situacao=StatusIndicacao.pendente.value,
                bonus=50.0,
            )
            session.add(modelo)
            session.commit()
            session.refresh(modelo)
            return Indicacao.model_validate(modelo)

    def buscar_por_id(self, indicacao_id: int) -> Optional[Indicacao]:
        with self._session_factory() as session:
            modelo = session.get(IndicacaoModel, indicacao_id)
            return Indicacao.model_validate(modelo) if modelo else None

    def listar_por_cliente(self, cliente_id: int) -> List[Indicacao]:
        with self._session_factory() as session:
            modelos = session.scalars(
                select(IndicacaoModel)
                .where(IndicacaoModel.cliente_id == cliente_id)
                .order_by(IndicacaoModel.id)
            ).all()
            return [Indicacao.model_validate(m) for m in modelos]

    def buscar_por_contato(self, contato: str) -> Optional[Indicacao]:
        with self._session_factory() as session:
            modelo = session.scalars(
                select(IndicacaoModel).where(func.lower(IndicacaoModel.contato) == contato.lower())
            ).first()
            return Indicacao.model_validate(modelo) if modelo else None

    def excluir(self, indicacao_id: int) -> bool:
        with self._session_factory() as session:
            modelo = session.get(IndicacaoModel, indicacao_id)
            if modelo is None:
                return False
            session.delete(modelo)
            session.commit()
            return True


indicacao_repository: IndicacaoRepository = SqlIndicacaoRepository(SessionLocal)
