"""
Camada de Persistência, ClienteRepository.

Contrato (Protocol) + InMemoryClienteRepository (testes unitários)
+ SqlClienteRepository (API, cliente_repository).
"""

import re
from typing import Protocol

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.database import SessionLocal
from app.db.models import ClienteModel
from app.domain.cliente import (
    Cliente,
    Endereco,
    StatusCliente,
)


CAMPOS_ENDERECO = (
    "cep",
    "logradouro",
    "numero",
    "complemento",
    "bairro",
    "cidade",
    "uf",
)


def _normalizar_cpf(cpf: str) -> str:
    """
    Remove todos os caracteres não numéricos do CPF.
    """

    return re.sub(r"\D", "", cpf)


def _normalizar_email(email: str) -> str:
    """
    Remove espaços externos e converte o e-mail
    para letras minúsculas.
    """

    return email.strip().lower()


class ClienteRepository(Protocol):
    """
    Contrato de persistência para clientes.
    """

    def listar(
        self,
        page: int = 1,
        limit: int = 20,
        status_filtro: StatusCliente | None = None,
    ) -> tuple[list[Cliente], int]:
        ...

    def buscar_por_id(
        self,
        cliente_id: str,
    ) -> Cliente | None:
        ...

    def buscar_por_cpf(
        self,
        cpf: str,
    ) -> Cliente | None:
        ...

    def buscar_por_email(
        self,
        email: str,
    ) -> Cliente | None:
        ...

    def criar(
        self,
        cliente: Cliente,
    ) -> Cliente:
        ...

    def atualizar(
        self,
        cliente: Cliente,
    ) -> Cliente:
        ...

    def remover(
        self,
        cliente_id: str,
    ) -> bool:
        ...


class InMemoryClienteRepository:
    """
    Implementação em memória utilizada principalmente
    nos testes unitários.
    """

    def __init__(self) -> None:
        self._clientes: dict[str, Cliente] = {}
        self._inicializar_dados_mock()

    def _inicializar_dados_mock(self) -> None:
        """
        Inicializa um cliente padrão para testes.
        """

        cliente_padrao = Cliente(
            id="8f1c2a6e-4b7d-4c1a-9f52-3d6a1b0c7e11",
            nome="Marcos Andrade",
            email="marcos.andrade@email.com",
            cpf="52998224725",
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

        self._clientes[
            cliente_padrao.id
        ] = cliente_padrao

    def listar(
        self,
        page: int = 1,
        limit: int = 20,
        status_filtro: StatusCliente | None = None,
    ) -> tuple[list[Cliente], int]:
        """
        Lista clientes com paginação
        e filtro opcional por status.
        """

        clientes = list(self._clientes.values())

        if status_filtro is not None:
            clientes = [
                cliente
                for cliente in clientes
                if cliente.status == status_filtro
            ]

        clientes.sort(
            key=lambda cliente: (
                cliente.criado_em,
                cliente.id,
            )
        )

        total = len(clientes)
        inicio = (page - 1) * limit
        fim = inicio + limit

        return clientes[inicio:fim], total

    def buscar_por_id(
        self,
        cliente_id: str,
    ) -> Cliente | None:
        """
        Busca um cliente pelo ID.
        """

        return self._clientes.get(cliente_id)

    def buscar_por_cpf(
        self,
        cpf: str,
    ) -> Cliente | None:
        """
        Busca um cliente pelo CPF.
        """

        cpf_normalizado = _normalizar_cpf(cpf)

        for cliente in self._clientes.values():
            cpf_cliente = _normalizar_cpf(
                cliente.cpf
            )

            if cpf_cliente == cpf_normalizado:
                return cliente

        return None

    def buscar_por_email(
        self,
        email: str,
    ) -> Cliente | None:
        """
        Busca um cliente pelo e-mail,
        ignorando espaços e diferenças entre maiúsculas
        e minúsculas.
        """

        email_normalizado = _normalizar_email(email)

        for cliente in self._clientes.values():
            email_cliente = _normalizar_email(
                cliente.email
            )

            if email_cliente == email_normalizado:
                return cliente

        return None

    def criar(
        self,
        cliente: Cliente,
    ) -> Cliente:
        """
        Cria um cliente em memória.
        """

        self._clientes[cliente.id] = cliente

        return cliente

    def atualizar(
        self,
        cliente: Cliente,
    ) -> Cliente:
        """
        Atualiza um cliente em memória.
        """

        self._clientes[cliente.id] = cliente

        return cliente

    def remover(
        self,
        cliente_id: str,
    ) -> bool:
        """
        Remove um cliente pelo ID.
        """

        if cliente_id not in self._clientes:
            return False

        del self._clientes[cliente_id]

        return True


class SqlClienteRepository:
    """
    Implementação do repository utilizando SQLAlchemy.

    O endereço é representado como um objeto no domínio,
    mas seus campos são armazenados diretamente nas
    colunas da tabela de clientes.
    """

    def __init__(
        self,
        session_factory: sessionmaker[Session],
    ) -> None:
        self._session_factory = session_factory

    @staticmethod
    def _para_dominio(
        modelo: ClienteModel,
    ) -> Cliente:
        """
        Converte um modelo SQLAlchemy em objeto de domínio.
        """

        dados_endereco = {
            campo: getattr(modelo, campo)
            for campo in CAMPOS_ENDERECO
        }

        return Cliente(
            id=modelo.id,
            nome=modelo.nome,
            email=modelo.email,
            cpf=modelo.cpf,
            telefone=modelo.telefone,
            endereco=Endereco(**dados_endereco),
            distribuidora=modelo.distribuidora,
            numero_instalacao=modelo.numero_instalacao,
            status=modelo.status,
            acesso_habilitado=modelo.acesso_habilitado,
            criado_em=modelo.criado_em,
        )

    @staticmethod
    def _copiar_para_modelo(
        cliente: Cliente,
        modelo: ClienteModel,
    ) -> None:
        """
        Copia os dados do objeto de domínio
        para o modelo SQLAlchemy.
        """

        dados_cliente = cliente.model_dump(
            mode="json",
            exclude={"endereco"},
        )

        dados_cliente["cpf"] = _normalizar_cpf(
            cliente.cpf
        )

        dados_cliente["email"] = _normalizar_email(
            cliente.email
        )

        dados_endereco = cliente.endereco.model_dump(
            mode="json"
        )

        dados_cliente.update(dados_endereco)

        for campo, valor in dados_cliente.items():
            setattr(
                modelo,
                campo,
                valor,
            )

    def listar(
        self,
        page: int = 1,
        limit: int = 20,
        status_filtro: StatusCliente | None = None,
    ) -> tuple[list[Cliente], int]:
        """
        Lista clientes com paginação
        e filtro opcional por status.
        """

        with self._session_factory() as session:
            consulta = select(ClienteModel)

            if status_filtro is not None:
                consulta = consulta.where(
                    ClienteModel.status
                    == status_filtro.value
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
                    ClienteModel.criado_em,
                    ClienteModel.id,
                )
                .offset((page - 1) * limit)
                .limit(limit)
            )

            modelos = session.scalars(
                consulta_paginada
            ).all()

            clientes = [
                self._para_dominio(modelo)
                for modelo in modelos
            ]

            return clientes, total

    def buscar_por_id(
        self,
        cliente_id: str,
    ) -> Cliente | None:
        """
        Busca um cliente pelo ID.
        """

        with self._session_factory() as session:
            modelo = session.get(
                ClienteModel,
                cliente_id,
            )

            if modelo is None:
                return None

            return self._para_dominio(modelo)

    def buscar_por_cpf(
        self,
        cpf: str,
    ) -> Cliente | None:
        """
        Busca um cliente pelo CPF normalizado.
        """

        cpf_normalizado = _normalizar_cpf(cpf)

        with self._session_factory() as session:
            consulta = select(
                ClienteModel
            ).where(
                ClienteModel.cpf == cpf_normalizado
            )

            modelo = session.scalars(
                consulta
            ).first()

            if modelo is None:
                return None

            return self._para_dominio(modelo)

    def buscar_por_email(
        self,
        email: str,
    ) -> Cliente | None:
        """
        Busca um cliente pelo e-mail,
        ignorando diferenças entre maiúsculas
        e minúsculas.
        """

        email_normalizado = _normalizar_email(email)

        with self._session_factory() as session:
            consulta = select(
                ClienteModel
            ).where(
                func.lower(ClienteModel.email)
                == email_normalizado
            )

            modelo = session.scalars(
                consulta
            ).first()

            if modelo is None:
                return None

            return self._para_dominio(modelo)

    def criar(
        self,
        cliente: Cliente,
    ) -> Cliente:
        """
        Cria um novo cliente.
        """

        with self._session_factory() as session:
            modelo = ClienteModel()

            self._copiar_para_modelo(
                cliente,
                modelo,
            )

            session.add(modelo)
            session.commit()
            session.refresh(modelo)

            return self._para_dominio(modelo)

    def atualizar(
        self,
        cliente: Cliente,
    ) -> Cliente:
        """
        Atualiza um cliente existente.

        Caso o cliente ainda não exista no banco,
        um novo registro é criado.
        """

        with self._session_factory() as session:
            modelo = session.get(
                ClienteModel,
                cliente.id,
            )

            if modelo is None:
                modelo = ClienteModel()
                session.add(modelo)

            self._copiar_para_modelo(
                cliente,
                modelo,
            )

            session.commit()
            session.refresh(modelo)

            return self._para_dominio(modelo)

    def remover(
        self,
        cliente_id: str,
    ) -> bool:
        """
        Remove o cliente.

        Os registros dependentes, como ativação,
        cartas e cupons, devem ser removidos pelo banco
        por meio de ON DELETE CASCADE.
        """

        with self._session_factory() as session:
            modelo = session.get(
                ClienteModel,
                cliente_id,
            )

            if modelo is None:
                return False

            session.delete(modelo)
            session.commit()

            return True


cliente_repository: ClienteRepository = (
    SqlClienteRepository(SessionLocal)
)
