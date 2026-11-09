"""
Camada de Persistência, AtivacaoRepository.

Contrato (Protocol) + InMemoryAtivacaoRepository (testes unitarios)
+ SqlAtivacaoRepository (API, ativacao_repository).
"""
from typing import Protocol

from sqlalchemy.orm import Session, sessionmaker

from app.db.database import SessionLocal
from app.db.models import AtivacaoModel
from app.domain.ativacao import AtivacaoCliente


class AtivacaoRepository(Protocol):
    def buscar_por_cliente_id(self, cliente_id: str) -> AtivacaoCliente | None: ...
    def salvar_ou_atualizar(self, ativacao: AtivacaoCliente) -> AtivacaoCliente: ...


class InMemoryAtivacaoRepository:
    def __init__(self) -> None:
        self._ativacoes: dict[str, AtivacaoCliente] = {}
        self._inicializar_mock()

    def _inicializar_mock(self) -> None:
        ativacao_padrao = AtivacaoCliente(
            cliente_id="8f1c2a6e-4b7d-4c1a-9f52-3d6a1b0c7e11",
            etapa_atual=2,
            distribuidora="CEMIG",
            prazo_ativacao_dias=90,
            previsao_conclusao="2026-07-31",
            atualizado_em="2026-08-18T08:00:00Z",
            observacoes=[],
        )
        self._ativacoes[ativacao_padrao.cliente_id] = ativacao_padrao

    def buscar_por_cliente_id(self, cliente_id: str) -> AtivacaoCliente | None:
        return self._ativacoes.get(cliente_id)

    def salvar_ou_atualizar(self, ativacao: AtivacaoCliente) -> AtivacaoCliente:
        self._ativacoes[ativacao.cliente_id] = ativacao
        return ativacao


class SqlAtivacaoRepository:
    """Uma linha por cliente em 'ativacoes' (cliente_id e PK e FK para clientes)."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def buscar_por_cliente_id(self, cliente_id: str) -> AtivacaoCliente | None:
        with self._session_factory() as session:
            modelo = session.get(AtivacaoModel, cliente_id)
            return AtivacaoCliente.model_validate(modelo) if modelo else None

    def salvar_ou_atualizar(self, ativacao: AtivacaoCliente) -> AtivacaoCliente:
        with self._session_factory() as session:
            modelo = session.get(AtivacaoModel, ativacao.cliente_id)
            if modelo is None:
                modelo = AtivacaoModel(cliente_id=ativacao.cliente_id)
                session.add(modelo)
            for campo, valor in ativacao.model_dump(mode="json").items():
                setattr(modelo, campo, valor)
            # Lista nova (copia): o SQLAlchemy so percebe mudanca numa coluna JSON
            # quando o objeto atribuido e outro.
            modelo.observacoes = list(ativacao.observacoes)
            session.commit()
            session.refresh(modelo)
            return AtivacaoCliente.model_validate(modelo)


ativacao_repository: AtivacaoRepository = SqlAtivacaoRepository(SessionLocal)
