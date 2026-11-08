"""
Camada de Persistência, ClienteRepository.

Contrato (Protocol) + InMemoryClienteRepository (testes unitarios)
+ SqlClienteRepository (API, cliente_repository).
"""
import re
from typing import Protocol

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.database import SessionLocal
from app.db.models import ClienteModel
from app.domain.cliente import Cliente, Endereco, StatusCliente

CAMPOS_ENDERECO = ("cep", "logradouro", "numero", "complemento", "bairro", "cidade", "uf")


class ClienteRepository(Protocol):
    def listar(
        self,
        page: int = 1,
        limit: int = 20,
        status_filtro: StatusCliente | None = None,
    ) -> tuple[list[Cliente], int]: ...
    def buscar_por_id(self, cliente_id: str) -> Cliente | None: ...
    def buscar_por_cpf(self, cpf: str) -> Cliente | None: ...
    def buscar_por_email(self, email: str) -> Cliente | None: ...
    def criar(self, cliente: Cliente) -> Cliente: ...
    def atualizar(self, cliente: Cliente) -> Cliente: ...
    def remover(self, cliente_id: str) -> bool: ...


def _normalizar_cpf(cpf: str) -> str:
    return re.sub(r"\D", "", cpf)


class InMemoryClienteRepository:
    def __init__(self) -> None:
        self._clientes: dict[str, Cliente] = {}
        self._inicializar_dados_mock()

    def _inicializar_dados_mock(self) -> None:
        cliente_padrao = Cliente(
            id="8f1c2a6e-4b7d-4c1a-9f52-3d6a1b0c7e11",
            nome="Marcos Andrade",
            email="marcos.andrade@email.com",
            cpf="12345678900",
            telefone="(31) 98888-1234",
            endereco=Endereco(
                cep="30130-010",
                logradouro="Av. Afonso Pena",
                numero="1000",
                complemento="Apto 302",
                bairro="Centro",
                cidade="Belo Horizonte",
                uf="MG",
            ),
            distribuidora="CEMIG",
            numero_instalacao="3001234567",
            status=StatusCliente.em_ativacao,
            acesso_habilitado=False,
            criado_em="2026-05-02T13:20:00Z",
        )
        self._clientes[cliente_padrao.id] = cliente_padrao

    def _normalizar_cpf(self, cpf: str) -> str:
        return _normalizar_cpf(cpf)

    def listar(
        self,
        page: int = 1,
        limit: int = 20,
        status_filtro: StatusCliente | None = None,
    ) -> tuple[list[Cliente], int]:
        todos = list(self._clientes.values())
        if status_filtro:
            todos = [c for c in todos if c.status == status_filtro]
        total = len(todos)
        inicio = (page - 1) * limit
        fim = inicio + limit
        return todos[inicio:fim], total

    def buscar_por_id(self, cliente_id: str) -> Cliente | None:
        return self._clientes.get(cliente_id)

    def buscar_por_cpf(self, cpf: str) -> Cliente | None:
        cpf_limpo = self._normalizar_cpf(cpf)
        for cliente in self._clientes.values():
            if self._normalizar_cpf(cliente.cpf) == cpf_limpo:
                return cliente
        return None

    def buscar_por_email(self, email: str) -> Cliente | None:
        email_limpo = email.strip().lower()
        for cliente in self._clientes.values():
            if cliente.email.strip().lower() == email_limpo:
                return cliente
        return None

    def criar(self, cliente: Cliente) -> Cliente:
        self._clientes[cliente.id] = cliente
        return cliente

    def atualizar(self, cliente: Cliente) -> Cliente:
        self._clientes[cliente.id] = cliente
        return cliente

    def remover(self, cliente_id: str) -> bool:
        if cliente_id in self._clientes:
            del self._clientes[cliente_id]
            return True
        return False


class SqlClienteRepository:
    """O endereco e um objeto no Dominio e colunas na tabela clientes."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    @staticmethod
    def _para_dominio(modelo: ClienteModel) -> Cliente:
        return Cliente(
            id=modelo.id,
            nome=modelo.nome,
            email=modelo.email,
            cpf=modelo.cpf,
            telefone=modelo.telefone,
            endereco=Endereco(**{campo: getattr(modelo, campo) for campo in CAMPOS_ENDERECO}),
            distribuidora=modelo.distribuidora,
            numero_instalacao=modelo.numero_instalacao,
            status=modelo.status,
            acesso_habilitado=modelo.acesso_habilitado,
            criado_em=modelo.criado_em,
        )

    @staticmethod
    def _copiar_para_modelo(cliente: Cliente, modelo: ClienteModel) -> None:
        dados = cliente.model_dump(mode="json", exclude={"endereco"})
        dados.update(cliente.endereco.model_dump(mode="json"))
        for campo, valor in dados.items():
            setattr(modelo, campo, valor)

    def listar(
        self,
        page: int = 1,
        limit: int = 20,
        status_filtro: StatusCliente | None = None,
    ) -> tuple[list[Cliente], int]:
        with self._session_factory() as session:
            consulta = select(ClienteModel)
            if status_filtro:
                consulta = consulta.where(ClienteModel.status == status_filtro.value)
            total = session.scalar(select(func.count()).select_from(consulta.subquery()))
            modelos = session.scalars(
                consulta.order_by(ClienteModel.criado_em, ClienteModel.id)
                .offset((page - 1) * limit)
                .limit(limit)
            ).all()
            return [self._para_dominio(m) for m in modelos], total or 0

    def buscar_por_id(self, cliente_id: str) -> Cliente | None:
        with self._session_factory() as session:
            modelo = session.get(ClienteModel, cliente_id)
            return self._para_dominio(modelo) if modelo else None

    def buscar_por_cpf(self, cpf: str) -> Cliente | None:
        with self._session_factory() as session:
            modelo = session.scalars(
                select(ClienteModel).where(ClienteModel.cpf == _normalizar_cpf(cpf))
            ).first()
            return self._para_dominio(modelo) if modelo else None

    def buscar_por_email(self, email: str) -> Cliente | None:
        with self._session_factory() as session:
            modelo = session.scalars(
                select(ClienteModel).where(func.lower(ClienteModel.email) == email.strip().lower())
            ).first()
            return self._para_dominio(modelo) if modelo else None

    def criar(self, cliente: Cliente) -> Cliente:
        with self._session_factory() as session:
            modelo = ClienteModel()
            self._copiar_para_modelo(cliente, modelo)
            session.add(modelo)
            session.commit()
            session.refresh(modelo)
            return self._para_dominio(modelo)

    def atualizar(self, cliente: Cliente) -> Cliente:
        with self._session_factory() as session:
            modelo = session.get(ClienteModel, cliente.id)
            if modelo is None:
                modelo = ClienteModel()
                session.add(modelo)
            self._copiar_para_modelo(cliente, modelo)
            session.commit()
            session.refresh(modelo)
            return self._para_dominio(modelo)

    def remover(self, cliente_id: str) -> bool:
        """Remove o cliente; o banco apaga ativacao, cartas e cupons dele (ON DELETE CASCADE)."""
        with self._session_factory() as session:
            modelo = session.get(ClienteModel, cliente_id)
            if modelo is None:
                return False
            session.delete(modelo)
            session.commit()
            return True


cliente_repository: ClienteRepository = SqlClienteRepository(SessionLocal)
