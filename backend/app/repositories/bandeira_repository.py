"""
Camada de Persistencia, BandeiraRepository.

Contrato (Protocol) + InMemoryBandeiraRepository (testes unitarios)
+ SqlBandeiraRepository (API, bandeira_repository).
"""

from datetime import datetime
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.db.database import SessionLocal
from app.db.models import BandeiraTarifariaModel
from app.domain.bandeira import (
    ADICIONAL_POR_KWH,
    BandeiraMes,
    BandeiraTarifaria,
)


def _para_dominio(
    mes_referencia: str,
    bandeira: str,
    atualizado_em: datetime | None,
) -> BandeiraMes:
    valor = BandeiraTarifaria(bandeira)

    return BandeiraMes(
        mes_referencia=mes_referencia,
        bandeira=valor,
        adicional_por_kwh=ADICIONAL_POR_KWH[valor],
        definida=True,
        atualizado_em=atualizado_em,
    )


class BandeiraRepository(Protocol):
    def listar(self) -> list[BandeiraMes]:
        ...

    def buscar(
        self,
        mes_referencia: str,
    ) -> BandeiraMes | None:
        ...

    def salvar(
        self,
        mes_referencia: str,
        bandeira: BandeiraTarifaria,
    ) -> BandeiraMes:
        ...


class InMemoryBandeiraRepository:
    def __init__(self) -> None:
        self._meses: dict[str, BandeiraMes] = {}

    def listar(self) -> list[BandeiraMes]:
        return [
            self._meses[mes]
            for mes in sorted(self._meses, reverse=True)
        ]

    def buscar(
        self,
        mes_referencia: str,
    ) -> BandeiraMes | None:
        return self._meses.get(mes_referencia)

    def salvar(
        self,
        mes_referencia: str,
        bandeira: BandeiraTarifaria,
    ) -> BandeiraMes:
        registro = _para_dominio(
            mes_referencia,
            bandeira.value,
            datetime.now(),
        )

        self._meses[mes_referencia] = registro

        return registro


class SqlBandeiraRepository:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
    ) -> None:
        self._session_factory = session_factory

    def listar(self) -> list[BandeiraMes]:
        with self._session_factory() as session:
            modelos = session.scalars(
                select(BandeiraTarifariaModel).order_by(
                    BandeiraTarifariaModel.mes_referencia.desc()
                )
            ).all()

            return [
                _para_dominio(
                    modelo.mes_referencia,
                    modelo.bandeira,
                    modelo.atualizado_em,
                )
                for modelo in modelos
            ]

    def buscar(
        self,
        mes_referencia: str,
    ) -> BandeiraMes | None:
        with self._session_factory() as session:
            modelo = session.get(
                BandeiraTarifariaModel,
                mes_referencia,
            )

            if modelo is None:
                return None

            return _para_dominio(
                modelo.mes_referencia,
                modelo.bandeira,
                modelo.atualizado_em,
            )

    def salvar(
        self,
        mes_referencia: str,
        bandeira: BandeiraTarifaria,
    ) -> BandeiraMes:
        with self._session_factory() as session:
            modelo = session.get(
                BandeiraTarifariaModel,
                mes_referencia,
            )

            if modelo is None:
                modelo = BandeiraTarifariaModel(
                    mes_referencia=mes_referencia,
                )
                session.add(modelo)

            modelo.bandeira = bandeira.value
            modelo.atualizado_em = datetime.now()

            session.commit()
            session.refresh(modelo)

            return _para_dominio(
                modelo.mes_referencia,
                modelo.bandeira,
                modelo.atualizado_em,
            )


bandeira_repository: BandeiraRepository = (
    SqlBandeiraRepository(SessionLocal)
)
