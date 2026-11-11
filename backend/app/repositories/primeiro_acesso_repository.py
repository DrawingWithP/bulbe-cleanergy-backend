"""
Camada de Persistência, PrimeiroAcessoRepository.

Contrato (Protocol) + InMemoryPrimeiroAcessoRepository (testes unitários)
+ SqlPrimeiroAcessoRepository (API, primeiro_acesso_repository).

Na versão SQL, os clientes são obtidos da tabela 'clientes',
a mesma utilizada pelo ClienteRepository.

Ao habilitar o acesso neste repositório, a alteração também
é exibida no endpoint GET /v1/clientes/{id}.
"""

import re
from datetime import timezone
from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.db.database import SessionLocal
from app.db.models import (
    ClienteModel,
    VerificacaoModel,
)
from app.domain.primeiro_acesso import Verificacao


def _normalizar_cpf(cpf: str) -> str:
    return re.sub(r"\D", "", cpf)


class PrimeiroAcessoRepository(Protocol):
    def buscar_cliente_por_cpf(
        self,
        cpf: str,
    ) -> dict[str, Any] | None:
        ...

    def salvar_verificacao(
        self,
        verificacao: Verificacao,
    ) -> Verificacao:
        ...

    def buscar_verificacao_por_id(
        self,
        verificacao_id: str,
    ) -> Verificacao | None:
        ...

    def atualizar_verificacao(
        self,
        verificacao: Verificacao,
    ) -> Verificacao:
        ...

    def habilitar_acesso_cliente(
        self,
        cliente_id: str,
    ) -> bool:
        ...


class InMemoryPrimeiroAcessoRepository:
    def __init__(self) -> None:
        self._verificacoes: dict[str, Verificacao] = {}

        self._clientes: dict[str, dict[str, Any]] = {
            "8f1c2a6e-4b7d-4c1a-9f52-3d6a1b0c7e11": {
                "id": "8f1c2a6e-4b7d-4c1a-9f52-3d6a1b0c7e11",
                "nome": "Marcos Andrade",
                "cpf": "52998224725",
                "telefone": "(31) 98888-1234",
                "email": "marcos.andrade@email.com",
                "acesso_habilitado": False,
            },
            "7b2c1a5d-3e8f-4a0b-8d61-2c5b0a9d6e22": {
                "id": "7b2c1a5d-3e8f-4a0b-8d61-2c5b0a9d6e22",
                "nome": "Ana Carolina Souza",
                "cpf": "11144477735",
                "telefone": "(31) 97777-4321",
                "email": "ana.souza@email.com",
                "acesso_habilitado": False,
            },
        }

    def buscar_cliente_por_cpf(
        self,
        cpf: str,
    ) -> dict[str, Any] | None:
        cpf_normalizado = _normalizar_cpf(cpf)

        for cliente in self._clientes.values():
            if (
                _normalizar_cpf(cliente["cpf"])
                == cpf_normalizado
            ):
                return cliente

        return None

    def adicionar_cliente_mock(
        self,
        cliente: dict[str, Any],
    ) -> None:
        cliente_id = str(cliente["id"])
        dados_cliente = dict(cliente)

        dados_cliente["id"] = cliente_id
        dados_cliente["cpf"] = _normalizar_cpf(
            str(dados_cliente["cpf"])
        )

        self._clientes[cliente_id] = dados_cliente

    def salvar_verificacao(
        self,
        verificacao: Verificacao,
    ) -> Verificacao:
        self._verificacoes[
            verificacao.id
        ] = verificacao

        return verificacao

    def buscar_verificacao_por_id(
        self,
        verificacao_id: str,
    ) -> Verificacao | None:
        return self._verificacoes.get(
            verificacao_id
        )

    def atualizar_verificacao(
        self,
        verificacao: Verificacao,
    ) -> Verificacao:
        self._verificacoes[
            verificacao.id
        ] = verificacao

        return verificacao

    def habilitar_acesso_cliente(
        self,
        cliente_id: str,
    ) -> bool:
        cliente = self._clientes.get(cliente_id)

        if cliente is None:
            return False

        cliente["acesso_habilitado"] = True

        return True


class SqlPrimeiroAcessoRepository:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
    ) -> None:
        self._session_factory = session_factory

    @staticmethod
    def _para_dominio(
        modelo: VerificacaoModel,
    ) -> Verificacao:
        verificacao = Verificacao.model_validate(
            modelo
        )

        # O SQLite não preserva informações de fuso horário.
        # As datas deste projeto são armazenadas em UTC.
        if verificacao.expira_em.tzinfo is None:
            verificacao.expira_em = (
                verificacao.expira_em.replace(
                    tzinfo=timezone.utc
                )
            )

        if verificacao.criado_em.tzinfo is None:
            verificacao.criado_em = (
                verificacao.criado_em.replace(
                    tzinfo=timezone.utc
                )
            )

        return verificacao

    @staticmethod
    def _copiar_para_modelo(
        verificacao: Verificacao,
        modelo: VerificacaoModel,
    ) -> None:
        dados = verificacao.model_dump()

        for campo, valor in dados.items():
            setattr(
                modelo,
                campo,
                valor.value if hasattr(valor, "value") else valor,
            )

    def buscar_cliente_por_cpf(
        self,
        cpf: str,
    ) -> dict[str, Any] | None:
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

            return {
                "id": modelo.id,
                "nome": modelo.nome,
                "cpf": modelo.cpf,
                "telefone": modelo.telefone,
                "email": modelo.email,
                "acesso_habilitado": (
                    modelo.acesso_habilitado
                ),
            }

    def salvar_verificacao(
        self,
        verificacao: Verificacao,
    ) -> Verificacao:
        return self._salvar_ou_atualizar_verificacao(
            verificacao
        )

    def buscar_verificacao_por_id(
        self,
        verificacao_id: str,
    ) -> Verificacao | None:
        with self._session_factory() as session:
            modelo = session.get(
                VerificacaoModel,
                verificacao_id,
            )

            if modelo is None:
                return None

            return self._para_dominio(modelo)

    def atualizar_verificacao(
        self,
        verificacao: Verificacao,
    ) -> Verificacao:
        return self._salvar_ou_atualizar_verificacao(
            verificacao
        )

    def _salvar_ou_atualizar_verificacao(
        self,
        verificacao: Verificacao,
    ) -> Verificacao:
        with self._session_factory() as session:
            modelo = session.get(
                VerificacaoModel,
                verificacao.id,
            )

            if modelo is None:
                modelo = VerificacaoModel(
                    id=verificacao.id
                )
                session.add(modelo)

            self._copiar_para_modelo(
                verificacao,
                modelo,
            )

            session.commit()
            session.refresh(modelo)

            return self._para_dominio(modelo)

    def habilitar_acesso_cliente(
        self,
        cliente_id: str,
    ) -> bool:
        with self._session_factory() as session:
            modelo = session.get(
                ClienteModel,
                cliente_id,
            )

            if modelo is None:
                return False

            modelo.acesso_habilitado = True

            session.commit()

            return True


# Instância compartilhada do repositório.
primeiro_acesso_repository: PrimeiroAcessoRepository = (
    SqlPrimeiroAcessoRepository(SessionLocal)
)
