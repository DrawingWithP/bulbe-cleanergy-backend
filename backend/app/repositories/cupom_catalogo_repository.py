"""
Camada de Persistencia, catalogo de cupons.

Contrato (Protocol) + InMemoryCupomCatalogoRepository (testes unitarios)
+ SqlCupomCatalogoRepository (API).
"""

from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.db.database import SessionLocal
from app.db.models import CupomCatalogoModel, ParceiroModel
from app.domain.cupom_catalogo import CupomCatalogo


class CupomCatalogoRepository(Protocol):
    def listar(
        self,
        parceiro_id: str | None = None,
        apenas_ativos: bool = False,
    ) -> list[CupomCatalogo]:
        ...

    def buscar_por_id(self, modelo_id: str) -> CupomCatalogo | None:
        ...

    def salvar(self, modelo: CupomCatalogo) -> CupomCatalogo:
        ...

    def remover(self, modelo_id: str) -> bool:
        ...


class InMemoryCupomCatalogoRepository:
    def __init__(self) -> None:
        self._modelos: dict[str, CupomCatalogo] = {}

    def listar(
        self,
        parceiro_id: str | None = None,
        apenas_ativos: bool = False,
    ) -> list[CupomCatalogo]:
        return [
            modelo
            for modelo in sorted(self._modelos.values(), key=lambda m: (m.criado_em, m.id))
            if (parceiro_id is None or modelo.parceiro_id == parceiro_id)
            and (not apenas_ativos or modelo.ativo)
        ]

    def buscar_por_id(self, modelo_id: str) -> CupomCatalogo | None:
        return self._modelos.get(modelo_id)

    def salvar(self, modelo: CupomCatalogo) -> CupomCatalogo:
        self._modelos[modelo.id] = modelo
        return modelo

    def remover(self, modelo_id: str) -> bool:
        return self._modelos.pop(modelo_id, None) is not None


class SqlCupomCatalogoRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    @staticmethod
    def _para_dominio(modelo: CupomCatalogoModel, parceiro_nome: str | None) -> CupomCatalogo:
        return CupomCatalogo(
            id=modelo.id,
            parceiro_id=modelo.parceiro_id,
            parceiro_nome=parceiro_nome,
            titulo=modelo.titulo,
            descricao=modelo.descricao,
            tag=modelo.tag,
            prefixo_codigo=modelo.prefixo_codigo,
            validade_dias=modelo.validade_dias,
            peso=modelo.peso,
            ativo=modelo.ativo,
            criado_em=modelo.criado_em,
            atualizado_em=modelo.atualizado_em,
        )

    def listar(
        self,
        parceiro_id: str | None = None,
        apenas_ativos: bool = False,
    ) -> list[CupomCatalogo]:
        with self._session_factory() as session:
            consulta = (
                select(CupomCatalogoModel, ParceiroModel.nome)
                .join(ParceiroModel, ParceiroModel.id == CupomCatalogoModel.parceiro_id)
                .order_by(CupomCatalogoModel.criado_em, CupomCatalogoModel.id)
            )
            if parceiro_id is not None:
                consulta = consulta.where(CupomCatalogoModel.parceiro_id == parceiro_id)
            if apenas_ativos:
                # Modelo ativo de parceiro ativo
                consulta = consulta.where(
                    CupomCatalogoModel.ativo.is_(True),
                    ParceiroModel.ativo.is_(True),
                )
            return [self._para_dominio(modelo, nome) for modelo, nome in session.execute(consulta).all()]

    def buscar_por_id(self, modelo_id: str) -> CupomCatalogo | None:
        with self._session_factory() as session:
            linha = session.execute(
                select(CupomCatalogoModel, ParceiroModel.nome)
                .join(ParceiroModel, ParceiroModel.id == CupomCatalogoModel.parceiro_id)
                .where(CupomCatalogoModel.id == modelo_id)
            ).first()
            return self._para_dominio(*linha) if linha else None

    def salvar(self, modelo: CupomCatalogo) -> CupomCatalogo:
        with self._session_factory() as session:
            linha = session.get(CupomCatalogoModel, modelo.id) or CupomCatalogoModel(id=modelo.id)
            for campo, valor in modelo.model_dump(exclude={"id", "parceiro_nome"}).items():
                setattr(linha, campo, valor)
            session.add(linha)
            session.commit()
        return self.buscar_por_id(modelo.id)

    def remover(self, modelo_id: str) -> bool:
        with self._session_factory() as session:
            linha = session.get(CupomCatalogoModel, modelo_id)
            if linha is None:
                return False
            session.delete(linha)
            session.commit()
            return True


cupom_catalogo_repository: CupomCatalogoRepository = SqlCupomCatalogoRepository(SessionLocal)
