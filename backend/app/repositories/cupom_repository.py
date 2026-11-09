"""
Camada de Persistência, CupomRepository.

Contrato (Protocol) + InMemoryCupomRepository (testes unitarios)
+ SqlCupomRepository (API, cupom_repository).
"""
from typing import Protocol

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.database import SessionLocal
from app.db.models import CupomModel
from app.domain.cupom import Cupom, ParceiroResumoCupom, SituacaoCupom


class CupomRepository(Protocol):
    def listar_por_cliente(
        self,
        cliente_id: str,
        page: int = 1,
        limit: int = 20,
        situacao: SituacaoCupom | None = None,
    ) -> tuple[list[Cupom], int]: ...
    def buscar_por_id(self, cupom_id: str) -> Cupom | None: ...
    def salvar(self, cupom: Cupom) -> Cupom: ...
    def atualizar(self, cupom: Cupom) -> Cupom: ...
    def descartar(self, cupom_id: str) -> bool: ...


class InMemoryCupomRepository:
    def __init__(self) -> None:
        self._cupons: dict[str, Cupom] = {}
        self._inicializar_mock()

    def _inicializar_mock(self) -> None:
        c1 = Cupom(
            id="f6b1d803-2e94-4a57-83cd-9b0e5a7c1d22",
            cliente_id="8f1c2a6e-4b7d-4c1a-9f52-3d6a1b0c7e11",
            carta_id="a7c4e2b9-5d31-4f80-9e6b-8c2a1d4f7b55",
            tag="PARCERIA DROGARIA ARAÚJO",
            titulo="15% de desconto na Araújo",
            descricao="Use o cupom em qualquer loja física ou no app da Araújo.",
            codigo="BULBE15",
            parceiro=ParceiroResumoCupom(
                id="1d2c3b4a-5e6f-4071-8293-a4b5c6d7e8f9",
                nome="Drogaria Araújo",
                categoria="Farmácia",
            ),
            situacao=SituacaoCupom.ativo,
            valido_ate="2026-11-15",
            dias_restantes=14,
            criado_em="2026-06-12T19:42:00Z",
        )
        self._cupons[c1.id] = c1

    def listar_por_cliente(
        self,
        cliente_id: str,
        page: int = 1,
        limit: int = 20,
        situacao: SituacaoCupom | None = None,
    ) -> tuple[list[Cupom], int]:
        todos = [
            c for c in self._cupons.values()
            if c.cliente_id == cliente_id and c.situacao != SituacaoCupom.descartado
        ]
        if situacao:
            todos = [c for c in todos if c.situacao == situacao]

        total = len(todos)
        inicio = (page - 1) * limit
        fim = inicio + limit
        return todos[inicio:fim], total

    def buscar_por_id(self, cupom_id: str) -> Cupom | None:
        c = self._cupons.get(cupom_id)
        if c and c.situacao != SituacaoCupom.descartado:
            return c
        return None

    def salvar(self, cupom: Cupom) -> Cupom:
        self._cupons[cupom.id] = cupom
        return cupom

    def atualizar(self, cupom: Cupom) -> Cupom:
        self._cupons[cupom.id] = cupom
        return cupom

    def descartar(self, cupom_id: str) -> bool:
        c = self._cupons.get(cupom_id)
        if c:
            c.situacao = SituacaoCupom.descartado
            return True
        return False


class SqlCupomRepository:
    """O parceiro e um objeto no Dominio e tres colunas (parceiro_*) na tabela cupons."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    @staticmethod
    def _para_dominio(modelo: CupomModel) -> Cupom:
        return Cupom(
            id=modelo.id,
            cliente_id=modelo.cliente_id,
            carta_id=modelo.carta_id,
            tag=modelo.tag,
            titulo=modelo.titulo,
            descricao=modelo.descricao,
            codigo=modelo.codigo,
            parceiro=ParceiroResumoCupom(
                id=modelo.parceiro_id,
                nome=modelo.parceiro_nome,
                categoria=modelo.parceiro_categoria,
            ),
            situacao=modelo.situacao,
            valido_ate=modelo.valido_ate,
            dias_restantes=modelo.dias_restantes,
            criado_em=modelo.criado_em,
            usado_em=modelo.usado_em,
        )

    @staticmethod
    def _copiar_para_modelo(cupom: Cupom, modelo: CupomModel) -> None:
        dados = cupom.model_dump(mode="json", exclude={"parceiro"})
        for campo, valor in dados.items():
            setattr(modelo, campo, valor)
        modelo.parceiro_id = cupom.parceiro.id
        modelo.parceiro_nome = cupom.parceiro.nome
        modelo.parceiro_categoria = cupom.parceiro.categoria

    def listar_por_cliente(
        self,
        cliente_id: str,
        page: int = 1,
        limit: int = 20,
        situacao: SituacaoCupom | None = None,
    ) -> tuple[list[Cupom], int]:
        with self._session_factory() as session:
            consulta = select(CupomModel).where(
                CupomModel.cliente_id == cliente_id,
                CupomModel.situacao != SituacaoCupom.descartado.value,
            )
            if situacao:
                consulta = consulta.where(CupomModel.situacao == situacao.value)
            total = session.scalar(select(func.count()).select_from(consulta.subquery()))
            modelos = session.scalars(
                consulta.order_by(CupomModel.criado_em, CupomModel.id)
                .offset((page - 1) * limit)
                .limit(limit)
            ).all()
            return [self._para_dominio(m) for m in modelos], total or 0

    def buscar_por_id(self, cupom_id: str) -> Cupom | None:
        with self._session_factory() as session:
            modelo = session.get(CupomModel, cupom_id)
            if modelo and modelo.situacao != SituacaoCupom.descartado.value:
                return self._para_dominio(modelo)
            return None

    def salvar(self, cupom: Cupom) -> Cupom:
        return self.atualizar(cupom)

    def atualizar(self, cupom: Cupom) -> Cupom:
        with self._session_factory() as session:
            modelo = session.get(CupomModel, cupom.id)
            if modelo is None:
                modelo = CupomModel()
                session.add(modelo)
            self._copiar_para_modelo(cupom, modelo)
            session.commit()
            session.refresh(modelo)
            return self._para_dominio(modelo)

    def descartar(self, cupom_id: str) -> bool:
        """Descarte logico: o cupom continua no banco com situacao 'descartado'."""
        with self._session_factory() as session:
            modelo = session.get(CupomModel, cupom_id)
            if modelo is None:
                return False
            modelo.situacao = SituacaoCupom.descartado.value
            session.commit()
            return True


cupom_repository: CupomRepository = SqlCupomRepository(SessionLocal)
