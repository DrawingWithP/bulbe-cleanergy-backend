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


def _normalizar_texto(texto: str) -> str:
    return texto.strip().lower()


class ParceiroRepository(Protocol):
    def listar(
        self,
        page: int = 1,
        limit: int = 20,
        categoria: str | None = None,
        ativo: bool | None = None,
    ) -> tuple[list[Parceiro], int]:
        ...

    def buscar_por_id(
        self,
        parceiro_id: str,
    ) -> Parceiro | None:
        ...

    def buscar_por_nome(
        self,
        nome: str,
    ) -> Parceiro | None:
        ...

    def criar(
        self,
        parceiro: Parceiro,
    ) -> Parceiro:
        ...

    def atualizar(
        self,
        parceiro: Parceiro,
    ) -> Parceiro:
        ...

    def remover(
        self,
        parceiro_id: str,
    ) -> bool:
        ...


class InMemoryParceiroRepository:
    def __init__(self) -> None:
        self._parceiros: dict[str, Parceiro] = {}
        self._inicializar_mock()

    def _inicializar_mock(self) -> None:
        parceiro_araujo = Parceiro(
            id="1d2c3b4a-5e6f-4071-8293-a4b5c6d7e8f9",
            nome="Drogaria Araújo",
            categoria="Farmácia",
            logo_url=(
                "https://cdn.bulbeenergia.com.br/"
                "parceiros/araujo.png"
            ),
            ativo=True,
            criado_em="2026-05-20T12:00:00Z",
        )

        parceiro_inter = Parceiro(
            id="2b3c4d5e-6f70-4812-9a3b-c4d5e6f70819",
            nome="Banco Inter",
            categoria="Banco",
            logo_url=(
                "https://cdn.bulbeenergia.com.br/"
                "parceiros/inter.png"
            ),
            ativo=True,
            criado_em="2026-05-21T10:00:00Z",
        )

        self._parceiros[
            parceiro_araujo.id
        ] = parceiro_araujo

        self._parceiros[
            parceiro_inter.id
        ] = parceiro_inter

    def listar(
        self,
        page: int = 1,
        limit: int = 20,
        categoria: str | None = None,
        ativo: bool | None = None,
    ) -> tuple[list[Parceiro], int]:
        parceiros = list(
            self._parceiros.values()
        )

        if categoria is not None:
            categoria_normalizada = _normalizar_texto(
                categoria
            )

            parceiros = [
                parceiro
                for parceiro in parceiros
                if _normalizar_texto(
                    parceiro.categoria
                ) == categoria_normalizada
            ]

        if ativo is not None:
            parceiros = [
                parceiro
                for parceiro in parceiros
                if parceiro.ativo == ativo
            ]

        parceiros.sort(
            key=lambda parceiro: (
                parceiro.criado_em,
                parceiro.id,
            )
        )

        total = len(parceiros)
        inicio = (page - 1) * limit
        fim = inicio + limit

        return parceiros[inicio:fim], total

    def buscar_por_id(
        self,
        parceiro_id: str,
    ) -> Parceiro | None:
        return self._parceiros.get(
            parceiro_id
        )

    def buscar_por_nome(
        self,
        nome: str,
    ) -> Parceiro | None:
        nome_normalizado = _normalizar_texto(
            nome
        )

        for parceiro in self._parceiros.values():
            if (
                _normalizar_texto(parceiro.nome)
                == nome_normalizado
            ):
                return parceiro

        return None

    def criar(
        self,
        parceiro: Parceiro,
    ) -> Parceiro:
        self._parceiros[
            parceiro.id
        ] = parceiro

        return parceiro

    def atualizar(
        self,
        parceiro: Parceiro,
    ) -> Parceiro:
        self._parceiros[
            parceiro.id
        ] = parceiro

        return parceiro

    def remover(
        self,
        parceiro_id: str,
    ) -> bool:
        if parceiro_id not in self._parceiros:
            return False

        del self._parceiros[parceiro_id]

        return True


class SqlParceiroRepository:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
    ) -> None:
        self._session_factory = session_factory

    def listar(
        self,
        page: int = 1,
        limit: int = 20,
        categoria: str | None = None,
        ativo: bool | None = None,
    ) -> tuple[list[Parceiro], int]:
        with self._session_factory() as session:
            consulta = select(
                ParceiroModel
            )

            if categoria is not None:
                categoria_normalizada = (
                    _normalizar_texto(categoria)
                )

                consulta = consulta.where(
                    func.lower(
                        ParceiroModel.categoria
                    ) == categoria_normalizada
                )

            if ativo is not None:
                consulta = consulta.where(
                    ParceiroModel.ativo == ativo
                )

            consulta_total = select(
                func.count()
            ).select_from(
                consulta.subquery()
            )

            total = session.scalar(
                consulta_total
            ) or 0

            consulta_paginada = (
                consulta
                .order_by(
                    ParceiroModel.criado_em,
                    ParceiroModel.id,
                )
                .offset((page - 1) * limit)
                .limit(limit)
            )

            modelos = session.scalars(
                consulta_paginada
            ).all()

            parceiros = [
                Parceiro.model_validate(modelo)
                for modelo in modelos
            ]

            return parceiros, total

    def buscar_por_id(
        self,
        parceiro_id: str,
    ) -> Parceiro | None:
        with self._session_factory() as session:
            modelo = session.get(
                ParceiroModel,
                parceiro_id,
            )

            if modelo is None:
                return None

            return Parceiro.model_validate(modelo)

    def buscar_por_nome(
        self,
        nome: str,
    ) -> Parceiro | None:
        nome_normalizado = _normalizar_texto(
            nome
        )

        # A comparação é feita no Python porque o lower()
        # do SQLite não trata corretamente todos os acentos.
        with self._session_factory() as session:
            modelos = session.scalars(
                select(ParceiroModel)
            ).all()

            for modelo in modelos:
                if (
                    _normalizar_texto(modelo.nome)
                    == nome_normalizado
                ):
                    return Parceiro.model_validate(
                        modelo
                    )

            return None

    def criar(
        self,
        parceiro: Parceiro,
    ) -> Parceiro:
        with self._session_factory() as session:
            modelo = ParceiroModel(
                **parceiro.model_dump(
                    mode="json"
                )
            )

            session.add(modelo)
            session.commit()
            session.refresh(modelo)

            return Parceiro.model_validate(
                modelo
            )

    def atualizar(
        self,
        parceiro: Parceiro,
    ) -> Parceiro:
        with self._session_factory() as session:
            modelo = session.get(
                ParceiroModel,
                parceiro.id,
            )

            if modelo is None:
                modelo = ParceiroModel(
                    id=parceiro.id
                )
                session.add(modelo)

            dados = parceiro.model_dump(
                mode="json"
            )

            for campo, valor in dados.items():
                setattr(
                    modelo,
                    campo,
                    valor,
                )

            session.commit()
            session.refresh(modelo)

            return Parceiro.model_validate(
                modelo
            )

    def remover(
        self,
        parceiro_id: str,
    ) -> bool:
        with self._session_factory() as session:
            modelo = session.get(
                ParceiroModel,
                parceiro_id,
            )

            if modelo is None:
                return False

            session.delete(modelo)
            session.commit()

            return True


parceiro_repository: ParceiroRepository = (
    SqlParceiroRepository(SessionLocal)
)
