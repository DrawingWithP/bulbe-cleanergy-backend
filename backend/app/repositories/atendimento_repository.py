"""
Camada de Persistencia, atendimentos e mensagens.

Contrato (Protocol) + InMemoryAtendimentoRepository (testes unitarios)
+ SqlAtendimentoRepository (API).
"""

from typing import Protocol

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.database import SessionLocal
from app.db.models import AtendimentoMensagemModel, AtendimentoModel, ClienteModel
from app.domain.atendimento import Atendimento, AtendimentoResumo, Mensagem


class AtendimentoRepository(Protocol):
    def salvar(self, atendimento: Atendimento) -> Atendimento:
        ...

    def buscar_por_id(self, atendimento_id: str) -> Atendimento | None:
        ...

    def listar(
        self,
        cliente_id: str | None = None,
        status: list[str] | None = None,
    ) -> list[AtendimentoResumo]:
        ...

    def adicionar_mensagem(
        self,
        atendimento_id: str,
        autor: str,
        texto: str,
        criado_em: str,
        opcoes: list[str] | None = None,
    ) -> Mensagem:
        ...

    def mensagens(self, atendimento_id: str, depois_de: int = 0) -> list[Mensagem]:
        ...


class InMemoryAtendimentoRepository:
    def __init__(self) -> None:
        self._atendimentos: dict[str, Atendimento] = {}
        self._mensagens: list[tuple[str, Mensagem]] = []

    def salvar(self, atendimento: Atendimento) -> Atendimento:
        self._atendimentos[atendimento.id] = atendimento
        return atendimento

    def buscar_por_id(self, atendimento_id: str) -> Atendimento | None:
        return self._atendimentos.get(atendimento_id)

    def listar(self, cliente_id=None, status=None) -> list[AtendimentoResumo]:
        itens = []
        for atendimento in self._atendimentos.values():
            if cliente_id and atendimento.cliente_id != cliente_id:
                continue
            if status and atendimento.status.value not in status:
                continue
            mensagens = self.mensagens(atendimento.id)
            itens.append(AtendimentoResumo(
                **atendimento.model_dump(),
                ultima_mensagem=mensagens[-1].texto if mensagens else None,
                total_mensagens=len(mensagens),
            ))
        return sorted(itens, key=lambda a: a.atualizado_em, reverse=True)

    def adicionar_mensagem(self, atendimento_id, autor, texto, criado_em, opcoes=None) -> Mensagem:
        mensagem = Mensagem(id=len(self._mensagens) + 1, autor=autor, texto=texto,
                            opcoes=opcoes, criado_em=criado_em)
        self._mensagens.append((atendimento_id, mensagem))
        return mensagem

    def mensagens(self, atendimento_id: str, depois_de: int = 0) -> list[Mensagem]:
        return [m for dono, m in self._mensagens if dono == atendimento_id and m.id > depois_de]


class SqlAtendimentoRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def salvar(self, atendimento: Atendimento) -> Atendimento:
        with self._session_factory() as session:
            modelo = session.get(AtendimentoModel, atendimento.id) or AtendimentoModel(id=atendimento.id)
            for campo, valor in atendimento.model_dump(mode="json", exclude={"id"}).items():
                setattr(modelo, campo, valor)
            session.add(modelo)
            session.commit()
        return atendimento

    def buscar_por_id(self, atendimento_id: str) -> Atendimento | None:
        with self._session_factory() as session:
            modelo = session.get(AtendimentoModel, atendimento_id)
            return Atendimento.model_validate(modelo) if modelo else None

    def listar(self, cliente_id=None, status=None) -> list[AtendimentoResumo]:
        with self._session_factory() as session:
            total = (
                select(AtendimentoMensagemModel.atendimento_id, func.count().label("total"),
                       func.max(AtendimentoMensagemModel.id).label("ultima"))
                .group_by(AtendimentoMensagemModel.atendimento_id)
                .subquery()
            )
            consulta = (
                select(AtendimentoModel, ClienteModel.nome, total.c.total, AtendimentoMensagemModel.texto)
                .join(ClienteModel, ClienteModel.id == AtendimentoModel.cliente_id)
                .outerjoin(total, total.c.atendimento_id == AtendimentoModel.id)
                .outerjoin(AtendimentoMensagemModel, AtendimentoMensagemModel.id == total.c.ultima)
                .order_by(AtendimentoModel.atualizado_em.desc())
            )
            if cliente_id:
                consulta = consulta.where(AtendimentoModel.cliente_id == cliente_id)
            if status:
                consulta = consulta.where(AtendimentoModel.status.in_(status))
            return [
                AtendimentoResumo(
                    **Atendimento.model_validate(modelo).model_dump(),
                    cliente_nome=nome,
                    total_mensagens=quantidade or 0,
                    ultima_mensagem=texto,
                )
                for modelo, nome, quantidade, texto in session.execute(consulta).all()
            ]

    def adicionar_mensagem(self, atendimento_id, autor, texto, criado_em, opcoes=None) -> Mensagem:
        with self._session_factory() as session:
            modelo = AtendimentoMensagemModel(
                atendimento_id=atendimento_id, autor=autor, texto=texto, opcoes=opcoes, criado_em=criado_em,
            )
            session.add(modelo)
            session.commit()
            session.refresh(modelo)
            return Mensagem.model_validate(modelo)

    def mensagens(self, atendimento_id: str, depois_de: int = 0) -> list[Mensagem]:
        with self._session_factory() as session:
            modelos = session.scalars(
                select(AtendimentoMensagemModel)
                .where(AtendimentoMensagemModel.atendimento_id == atendimento_id,
                       AtendimentoMensagemModel.id > depois_de)
                .order_by(AtendimentoMensagemModel.id)
            ).all()
            return [Mensagem.model_validate(m) for m in modelos]


atendimento_repository: AtendimentoRepository = SqlAtendimentoRepository(SessionLocal)
