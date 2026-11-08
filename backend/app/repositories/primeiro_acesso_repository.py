"""
Camada de Persistência, PrimeiroAcessoRepository.

Contrato (Protocol) + InMemoryPrimeiroAcessoRepository (testes unitarios)
+ SqlPrimeiroAcessoRepository (API, primeiro_acesso_repository).

Na versao SQL os clientes vem da tabela 'clientes' (a mesma do ClienteRepository),
e nao mais de uma lista propria: habilitar o acesso aqui aparece no GET /v1/clientes/{id}.
"""
import re
from datetime import timezone
from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.db.database import SessionLocal
from app.db.models import ClienteModel, VerificacaoModel
from app.domain.primeiro_acesso import Verificacao


class PrimeiroAcessoRepository(Protocol):
    def buscar_cliente_por_cpf(self, cpf: str) -> dict[str, Any] | None: ...
    def salvar_verificacao(self, verificacao: Verificacao) -> Verificacao: ...
    def buscar_verificacao_por_id(self, verificacao_id: str) -> Verificacao | None: ...
    def atualizar_verificacao(self, verificacao: Verificacao) -> Verificacao: ...
    def habilitar_acesso_cliente(self, cliente_id: str) -> bool: ...


def _normalizar_cpf(cpf: str) -> str:
    return re.sub(r"\D", "", cpf)


class InMemoryPrimeiroAcessoRepository:
    def __init__(self) -> None:
        self._verificacoes: dict[str, Verificacao] = {}
        # Base inicial de clientes simulados cadastrados na Bulbe
        self._clientes: list[dict[str, Any]] = [
            {
                "id": "8f1c2a6e-4b7d-4c1a-9f52-3d6a1b0c7e11",
                "nome": "Marcos Andrade",
                "cpf": "12345678900",
                "telefone": "(31) 98888-1234",
                "email": "marcos.andrade@email.com",
                "acesso_habilitado": False,
            },
            {
                "id": "7b2c1a5d-3e8f-4a0b-8d61-2c5b0a9d6e22",
                "nome": "Ana Carolina Souza",
                "cpf": "98765432100",
                "telefone": "(31) 97777-4321",
                "email": "ana.souza@email.com",
                "acesso_habilitado": False,
            },
        ]

    def _normalizar_cpf(self, cpf: str) -> str:
        return _normalizar_cpf(cpf)

    def buscar_cliente_por_cpf(self, cpf: str) -> dict[str, Any] | None:
        """Busca um cliente cadastrado pelo CPF (apenas dígitos)."""
        cpf_limpo = self._normalizar_cpf(cpf)
        for cliente in self._clientes:
            if self._normalizar_cpf(cliente["cpf"]) == cpf_limpo:
                return cliente
        return None

    def adicionar_cliente_mock(self, cliente: dict[str, Any]) -> None:
        """Adiciona ou atualiza um cliente mock para fins de teste."""
        self._clientes.append(cliente)

    def salvar_verificacao(self, verificacao: Verificacao) -> Verificacao:
        """Salva uma nova verificação."""
        self._verificacoes[verificacao.id] = verificacao
        return verificacao

    def buscar_verificacao_por_id(self, verificacao_id: str) -> Verificacao | None:
        """Retorna uma verificação existente pelo ID."""
        return self._verificacoes.get(verificacao_id)

    def atualizar_verificacao(self, verificacao: Verificacao) -> Verificacao:
        """Atualiza o registro de verificação."""
        self._verificacoes[verificacao.id] = verificacao
        return verificacao

    def habilitar_acesso_cliente(self, cliente_id: str) -> bool:
        """Marca o acesso do cliente como habilitado."""
        for cliente in self._clientes:
            if cliente["id"] == cliente_id:
                cliente["acesso_habilitado"] = True
                return True
        return False


class SqlPrimeiroAcessoRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    @staticmethod
    def _para_dominio(modelo: VerificacaoModel) -> Verificacao:
        verificacao = Verificacao.model_validate(modelo)
        # O SQLite nao guarda fuso horario: as datas foram gravadas em UTC.
        if verificacao.expira_em.tzinfo is None:
            verificacao.expira_em = verificacao.expira_em.replace(tzinfo=timezone.utc)
        if verificacao.criado_em.tzinfo is None:
            verificacao.criado_em = verificacao.criado_em.replace(tzinfo=timezone.utc)
        return verificacao

    def buscar_cliente_por_cpf(self, cpf: str) -> dict[str, Any] | None:
        """Busca um cliente cadastrado pelo CPF (apenas dígitos)."""
        with self._session_factory() as session:
            modelo = session.scalars(
                select(ClienteModel).where(ClienteModel.cpf == _normalizar_cpf(cpf))
            ).first()
            if modelo is None:
                return None
            return {
                "id": modelo.id,
                "nome": modelo.nome,
                "cpf": modelo.cpf,
                "telefone": modelo.telefone,
                "email": modelo.email,
                "acesso_habilitado": modelo.acesso_habilitado,
            }

    def salvar_verificacao(self, verificacao: Verificacao) -> Verificacao:
        return self.atualizar_verificacao(verificacao)

    def buscar_verificacao_por_id(self, verificacao_id: str) -> Verificacao | None:
        with self._session_factory() as session:
            modelo = session.get(VerificacaoModel, verificacao_id)
            return self._para_dominio(modelo) if modelo else None

    def atualizar_verificacao(self, verificacao: Verificacao) -> Verificacao:
        with self._session_factory() as session:
            modelo = session.get(VerificacaoModel, verificacao.id)
            if modelo is None:
                modelo = VerificacaoModel(id=verificacao.id)
                session.add(modelo)
            for campo, valor in verificacao.model_dump().items():
                setattr(modelo, campo, valor.value if hasattr(valor, "value") else valor)
            session.commit()
            session.refresh(modelo)
            return self._para_dominio(modelo)

    def habilitar_acesso_cliente(self, cliente_id: str) -> bool:
        with self._session_factory() as session:
            modelo = session.get(ClienteModel, cliente_id)
            if modelo is None:
                return False
            modelo.acesso_habilitado = True
            session.commit()
            return True


# Instância compartilhada do repositório
primeiro_acesso_repository: PrimeiroAcessoRepository = SqlPrimeiroAcessoRepository(SessionLocal)
