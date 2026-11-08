"""
Camada de Persistência, CartaRepository.

Contrato (Protocol) + InMemoryCartaRepository (testes unitarios)
+ SqlCartaRepository (API, carta_repository).

Tambem guarda a ofensiva do Clube Bulbe (semanas seguidas abrindo a carta),
que antes ficava num dicionario dentro do CartaService e se perdia a cada reinicio.
"""
from typing import Protocol

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.database import SessionLocal
from app.db.models import CartaModel, OfensivaClubeModel
from app.domain.carta import Carta, SituacaoCarta, TipoCarta


class CartaRepository(Protocol):
    def listar_por_cliente(
        self,
        cliente_id: str,
        page: int = 1,
        limit: int = 20,
        situacao: SituacaoCarta | None = None,
    ) -> tuple[list[Carta], int]: ...
    def buscar_por_id(self, carta_id: str) -> Carta | None: ...
    def buscar_disponivel_cliente(self, cliente_id: str) -> Carta | None: ...
    def salvar(self, carta: Carta) -> Carta: ...
    def atualizar(self, carta: Carta) -> Carta: ...
    def obter_sequencia(self, cliente_id: str) -> int | None: ...
    def salvar_sequencia(self, cliente_id: str, semanas: int) -> None: ...


class InMemoryCartaRepository:
    def __init__(self) -> None:
        self._cartas: dict[str, Carta] = {}
        self._sequencias: dict[str, int] = {}
        self._inicializar_mock()

    def _inicializar_mock(self) -> None:
        c1 = Carta(
            id="a7c4e2b9-5d31-4f80-9e6b-8c2a1d4f7b55",
            cliente_id="8f1c2a6e-4b7d-4c1a-9f52-3d6a1b0c7e11",
            semana=3,
            tipo=TipoCarta.normal,
            situacao=SituacaoCarta.disponivel,
            disponivel_em="2026-06-12T09:00:00Z",
            aberta_em=None,
            cupom_id=None,
        )
        self._cartas[c1.id] = c1
        self._sequencias[c1.cliente_id] = 3

    def listar_por_cliente(
        self,
        cliente_id: str,
        page: int = 1,
        limit: int = 20,
        situacao: SituacaoCarta | None = None,
    ) -> tuple[list[Carta], int]:
        todos = [c for c in self._cartas.values() if c.cliente_id == cliente_id]
        if situacao:
            todos = [c for c in todos if c.situacao == situacao]

        total = len(todos)
        inicio = (page - 1) * limit
        fim = inicio + limit
        return todos[inicio:fim], total

    def buscar_por_id(self, carta_id: str) -> Carta | None:
        return self._cartas.get(carta_id)

    def buscar_disponivel_cliente(self, cliente_id: str) -> Carta | None:
        for c in self._cartas.values():
            if c.cliente_id == cliente_id and c.situacao == SituacaoCarta.disponivel:
                return c
        return None

    def salvar(self, carta: Carta) -> Carta:
        self._cartas[carta.id] = carta
        return carta

    def atualizar(self, carta: Carta) -> Carta:
        self._cartas[carta.id] = carta
        return carta

    def obter_sequencia(self, cliente_id: str) -> int | None:
        return self._sequencias.get(cliente_id)

    def salvar_sequencia(self, cliente_id: str, semanas: int) -> None:
        self._sequencias[cliente_id] = semanas


class SqlCartaRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def listar_por_cliente(
        self,
        cliente_id: str,
        page: int = 1,
        limit: int = 20,
        situacao: SituacaoCarta | None = None,
    ) -> tuple[list[Carta], int]:
        with self._session_factory() as session:
            consulta = select(CartaModel).where(CartaModel.cliente_id == cliente_id)
            if situacao:
                consulta = consulta.where(CartaModel.situacao == situacao.value)
            total = session.scalar(select(func.count()).select_from(consulta.subquery()))
            modelos = session.scalars(
                consulta.order_by(CartaModel.semana, CartaModel.id)
                .offset((page - 1) * limit)
                .limit(limit)
            ).all()
            return [Carta.model_validate(m) for m in modelos], total or 0

    def buscar_por_id(self, carta_id: str) -> Carta | None:
        with self._session_factory() as session:
            modelo = session.get(CartaModel, carta_id)
            return Carta.model_validate(modelo) if modelo else None

    def buscar_disponivel_cliente(self, cliente_id: str) -> Carta | None:
        with self._session_factory() as session:
            modelo = session.scalars(
                select(CartaModel)
                .where(
                    CartaModel.cliente_id == cliente_id,
                    CartaModel.situacao == SituacaoCarta.disponivel.value,
                )
                .order_by(CartaModel.semana)
            ).first()
            return Carta.model_validate(modelo) if modelo else None

    def salvar(self, carta: Carta) -> Carta:
        return self.atualizar(carta)

    def atualizar(self, carta: Carta) -> Carta:
        with self._session_factory() as session:
            modelo = session.get(CartaModel, carta.id)
            if modelo is None:
                modelo = CartaModel(id=carta.id)
                session.add(modelo)
            for campo, valor in carta.model_dump(mode="json").items():
                setattr(modelo, campo, valor)
            session.commit()
            session.refresh(modelo)
            return Carta.model_validate(modelo)

    def obter_sequencia(self, cliente_id: str) -> int | None:
        with self._session_factory() as session:
            modelo = session.get(OfensivaClubeModel, cliente_id)
            return modelo.semanas_sequencia if modelo else None

    def salvar_sequencia(self, cliente_id: str, semanas: int) -> None:
        with self._session_factory() as session:
            modelo = session.get(OfensivaClubeModel, cliente_id)
            if modelo is None:
                modelo = OfensivaClubeModel(cliente_id=cliente_id)
                session.add(modelo)
            modelo.semanas_sequencia = semanas
            session.commit()


carta_repository: CartaRepository = SqlCartaRepository(SessionLocal)
