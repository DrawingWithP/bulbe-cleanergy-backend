"""
Camada de Persistência, CartaRepository.

Contrato (Protocol) + InMemoryCartaRepository (testes unitários)
+ SqlCartaRepository (API, carta_repository).

Também guarda a ofensiva do Clube Bulbe, que representa
as semanas seguidas em que o cliente abriu uma carta.
A ofensiva é persistida para não se perder a cada reinício.
"""

from typing import Protocol

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.database import SessionLocal
from app.db.models import (
    CartaModel,
    OfensivaClubeModel,
)
from app.domain.carta import (
    Carta,
    SituacaoCarta,
    TipoCarta,
)


class CartaRepository(Protocol):
    """
    Contrato de persistência para cartas
    e sequências de ofensiva.
    """

    def listar_por_cliente(
        self,
        cliente_id: str,
        page: int = 1,
        limit: int = 20,
        situacao: SituacaoCarta | None = None,
    ) -> tuple[list[Carta], int]:
        ...

    def buscar_por_id(
        self,
        carta_id: str,
    ) -> Carta | None:
        ...

    def buscar_disponivel_cliente(
        self,
        cliente_id: str,
    ) -> Carta | None:
        ...

    def salvar(
        self,
        carta: Carta,
    ) -> Carta:
        ...

    def atualizar(
        self,
        carta: Carta,
    ) -> Carta:
        ...

    def obter_sequencia(
        self,
        cliente_id: str,
    ) -> int | None:
        ...

    def salvar_sequencia(
        self,
        cliente_id: str,
        semanas: int,
    ) -> None:
        ...


class InMemoryCartaRepository:
    """
    Implementação em memória utilizada principalmente
    nos testes unitários.
    """

    def __init__(self) -> None:
        self._cartas: dict[str, Carta] = {}
        self._sequencias: dict[str, int] = {}
        self._inicializar_mock()

    def _inicializar_mock(self) -> None:
        """
        Inicializa uma carta padrão para testes.
        """

        carta_padrao = Carta(
            id="a7c4e2b9-5d31-4f80-9e6b-8c2a1d4f7b55",
            cliente_id=(
                "8f1c2a6e-4b7d-4c1a-9f52-3d6a1b0c7e11"
            ),
            semana=3,
            tipo=TipoCarta.normal,
            situacao=SituacaoCarta.disponivel,
            disponivel_em="2026-06-12T09:00:00Z",
            aberta_em=None,
            cupom_id=None,
        )

        self._cartas[carta_padrao.id] = carta_padrao
        self._sequencias[carta_padrao.cliente_id] = 3

    def listar_por_cliente(
        self,
        cliente_id: str,
        page: int = 1,
        limit: int = 20,
        situacao: SituacaoCarta | None = None,
    ) -> tuple[list[Carta], int]:
        """
        Lista as cartas de um cliente com paginação
        e filtro opcional por situação.
        """

        cartas = [
            carta
            for carta in self._cartas.values()
            if carta.cliente_id == cliente_id
        ]

        if situacao is not None:
            cartas = [
                carta
                for carta in cartas
                if carta.situacao == situacao
            ]

        cartas.sort(
            key=lambda carta: (
                carta.semana,
                carta.id,
            )
        )

        total = len(cartas)
        inicio = (page - 1) * limit
        fim = inicio + limit

        return cartas[inicio:fim], total

    def buscar_por_id(
        self,
        carta_id: str,
    ) -> Carta | None:
        """
        Busca uma carta pelo ID.
        """

        return self._cartas.get(carta_id)

    def buscar_disponivel_cliente(
        self,
        cliente_id: str,
    ) -> Carta | None:
        """
        Busca a primeira carta disponível do cliente,
        ordenada pelo número da semana.
        """

        cartas_disponiveis = [
            carta
            for carta in self._cartas.values()
            if (
                carta.cliente_id == cliente_id
                and carta.situacao
                == SituacaoCarta.disponivel
            )
        ]

        if not cartas_disponiveis:
            return None

        cartas_disponiveis.sort(
            key=lambda carta: (
                carta.semana,
                carta.id,
            )
        )

        return cartas_disponiveis[0]

    def salvar(
        self,
        carta: Carta,
    ) -> Carta:
        """
        Salva uma nova carta em memória.
        """

        self._cartas[carta.id] = carta

        return carta

    def atualizar(
        self,
        carta: Carta,
    ) -> Carta:
        """
        Atualiza uma carta existente em memória.
        """

        self._cartas[carta.id] = carta

        return carta

    def obter_sequencia(
        self,
        cliente_id: str,
    ) -> int | None:
        """
        Retorna a sequência de ofensiva do cliente.
        """

        return self._sequencias.get(cliente_id)

    def salvar_sequencia(
        self,
        cliente_id: str,
        semanas: int,
    ) -> None:
        """
        Salva a sequência de ofensiva do cliente.
        """

        self._sequencias[cliente_id] = semanas


class SqlCartaRepository:
    """
    Implementação do repository utilizando SQLAlchemy.
    """

    def __init__(
        self,
        session_factory: sessionmaker[Session],
    ) -> None:
        self._session_factory = session_factory

    def listar_por_cliente(
        self,
        cliente_id: str,
        page: int = 1,
        limit: int = 20,
        situacao: SituacaoCarta | None = None,
    ) -> tuple[list[Carta], int]:
        """
        Lista as cartas de um cliente com paginação
        e filtro opcional por situação.
        """

        with self._session_factory() as session:
            consulta = select(CartaModel).where(
                CartaModel.cliente_id == cliente_id
            )

            if situacao is not None:
                consulta = consulta.where(
                    CartaModel.situacao == situacao.value
                )

            consulta_total = select(
                func.count()
            ).select_from(
                consulta.subquery()
            )

            total = session.scalar(consulta_total) or 0

            consulta_paginada = (
                consulta
                .order_by(
                    CartaModel.semana,
                    CartaModel.id,
                )
                .offset((page - 1) * limit)
                .limit(limit)
            )

            modelos = session.scalars(
                consulta_paginada
            ).all()

            cartas = [
                Carta.model_validate(modelo)
                for modelo in modelos
            ]

            return cartas, total

    def buscar_por_id(
        self,
        carta_id: str,
    ) -> Carta | None:
        """
        Busca uma carta pelo ID.
        """

        with self._session_factory() as session:
            modelo = session.get(
                CartaModel,
                carta_id,
            )

            if modelo is None:
                return None

            return Carta.model_validate(modelo)

    def buscar_disponivel_cliente(
        self,
        cliente_id: str,
    ) -> Carta | None:
        """
        Busca a primeira carta disponível do cliente.
        """

        with self._session_factory() as session:
            consulta = (
                select(CartaModel)
                .where(
                    CartaModel.cliente_id == cliente_id,
                    CartaModel.situacao
                    == SituacaoCarta.disponivel.value,
                )
                .order_by(
                    CartaModel.semana,
                    CartaModel.id,
                )
            )

            modelo = session.scalars(
                consulta
            ).first()

            if modelo is None:
                return None

            return Carta.model_validate(modelo)

    def salvar(
        self,
        carta: Carta,
    ) -> Carta:
        """
        Salva uma nova carta.

        Caso o ID já exista, os dados da carta
        correspondente são atualizados.
        """

        return self._salvar_ou_atualizar(carta)

    def atualizar(
        self,
        carta: Carta,
    ) -> Carta:
        """
        Atualiza uma carta existente.

        Caso o ID ainda não exista, uma nova carta
        é criada para manter o comportamento de upsert.
        """

        return self._salvar_ou_atualizar(carta)

    def _salvar_ou_atualizar(
        self,
        carta: Carta,
    ) -> Carta:
        """
        Centraliza a persistência de uma carta.
        """

        with self._session_factory() as session:
            modelo = session.get(
                CartaModel,
                carta.id,
            )

            if modelo is None:
                modelo = CartaModel(id=carta.id)
                session.add(modelo)

            dados_carta = carta.model_dump(
                mode="json"
            )

            for campo, valor in dados_carta.items():
                setattr(
                    modelo,
                    campo,
                    valor,
                )

            session.commit()
            session.refresh(modelo)

            return Carta.model_validate(modelo)

    def obter_sequencia(
        self,
        cliente_id: str,
    ) -> int | None:
        """
        Retorna a sequência de ofensiva do cliente.
        """

        with self._session_factory() as session:
            modelo = session.get(
                OfensivaClubeModel,
                cliente_id,
            )

            if modelo is None:
                return None

            return modelo.semanas_sequencia

    def salvar_sequencia(
        self,
        cliente_id: str,
        semanas: int,
    ) -> None:
        """
        Cria ou atualiza a sequência de ofensiva
        do cliente.
        """

        with self._session_factory() as session:
            modelo = session.get(
                OfensivaClubeModel,
                cliente_id,
            )

            if modelo is None:
                modelo = OfensivaClubeModel(
                    cliente_id=cliente_id
                )
                session.add(modelo)

            modelo.semanas_sequencia = semanas

            session.commit()


# Uma única instância compartilhada por toda a aplicação.
carta_repository: CartaRepository = (
    SqlCartaRepository(SessionLocal)
)
