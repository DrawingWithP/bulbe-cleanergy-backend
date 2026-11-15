"""
Camada de Servico, AdesaoService.
"""

import re

from app.domain.adesao import (
    StatusAdesao,
    Adesao,
    AdesaoCreate,
    AdesaoUpdate,
)
from app.repositories.adesao_repository import (
    AdesaoRepository,
    adesao_repository,
)


class ErroDeNegocio(Exception):
    """
    Erro de negocio com formato padronizado:
    code, message e status.
    """

    def __init__(
        self,
        code: str,
        message: str,
        status: int,
    ) -> None:
        self.code = code
        self.message = message
        self.status = status
        super().__init__(message)


def _normalizar_cpf(
    cpf: str,
) -> str:
    """
    Remove caracteres nao numericos do CPF.
    """

    return re.sub(r"\D", "", cpf)


def _cliente_da_adesao(adesao):
    """Monta o cadastro do cliente com os dados da adesao."""
    from app.domain.cliente import ClienteCreate, Endereco

    telefone = "".join(c for c in adesao.telefone if c.isdigit())
    cep = "".join(c for c in adesao.cep if c.isdigit())
    return ClienteCreate(
        nome=adesao.nome,
        email=adesao.email,
        cpf=adesao.cpf,
        telefone=telefone if len(telefone) >= 10 else f"31{telefone}"[:11],
        endereco=Endereco(
            cep=f"{cep[:5]}-{cep[5:]}" if len(cep) == 8 else adesao.cep,
            logradouro=adesao.logradouro,
            numero=str(adesao.numero),
            complemento=None,
            bairro=adesao.bairro,
            cidade=adesao.cidade,
            uf=adesao.uf.upper(),
        ),
        distribuidora=adesao.distribuidora,
        numero_instalacao=adesao.numero_instalacao,
    )


class AdesaoService:
    def __init__(
        self,
        repository: AdesaoRepository,
    ) -> None:
        self._repository = repository

    def listar(self) -> list[Adesao]:
        """
        Lista todas as adesoes cadastradas.
        """

        return self._repository.listar()

    def buscar_por_id(
        self,
        adesao_id: int,
    ) -> Adesao:
        """
        Busca uma adesao pelo ID.
        """

        adesao = self._repository.buscar_por_id(
            adesao_id
        )

        if adesao is None:
            raise ErroDeNegocio(
                code="RECURSO_NAO_ENCONTRADO",
                message=(
                    f"Adesao com id {adesao_id} "
                    "nao foi encontrada."
                ),
                status=404,
            )

        return adesao

    def criar(
        self,
        dados: AdesaoCreate,
    ) -> Adesao:
        """
        Cria uma nova adesao, impedindo
        o cadastro duplicado de CPF.
        """

        cpf_informado = _normalizar_cpf(
            dados.cpf
        )

        for adesao in self._repository.listar():
            if (
                _normalizar_cpf(adesao.cpf)
                == cpf_informado
            ):
                raise ErroDeNegocio(
                    code="CPF_JA_CADASTRADO",
                    message=(
                        "Ja existe uma adesao cadastrada "
                        f"com o CPF {dados.cpf}."
                    ),
                    status=409,
                )

        return self._repository.criar(
            dados
        )

    def atualizar(
        self,
        adesao_id: int,
        dados: AdesaoUpdate,
    ) -> Adesao:
        """
        Atualiza uma adesao existente.
        """

        adesao_atualizada = (
            self._repository.atualizar(
                adesao_id,
                dados,
            )
        )

        if adesao_atualizada is None:
            raise ErroDeNegocio(
                code="RECURSO_NAO_ENCONTRADO",
                message=(
                    f"Adesao com id {adesao_id} "
                    "nao foi encontrada."
                ),
                status=404,
            )

        return adesao_atualizada

    def remover(
        self,
        adesao_id: int,
    ) -> None:
        """
        Remove uma adesao pelo ID.
        """

        removida = self._repository.remover(
            adesao_id
        )

        if not removida:
            raise ErroDeNegocio(
                code="RECURSO_NAO_ENCONTRADO",
                message=(
                    f"Adesao com id {adesao_id} "
                    "nao foi encontrada."
                ),
                status=404,
            )


    def _exigir_enviada(self, adesao: Adesao) -> None:
        if adesao.status not in (StatusAdesao.enviada, StatusAdesao.rascunho):
            raise ErroDeNegocio(
                code="ADESAO_JA_ANALISADA",
                message=f"Esta adesao ja foi {adesao.status.value}.",
                status=409,
            )

    def aprovar(self, adesao_id: int) -> tuple[Adesao, str]:
        """
        Aprova a adesao: cria o cliente com os dados dela (a jornada de
        ativacao comeca na etapa 1) e marca a adesao como aprovada.
        """

        from app.services.cliente_service import (
            ErroDeNegocio as ErroCliente,
            cliente_service,
        )

        adesao = self.buscar_por_id(adesao_id)
        self._exigir_enviada(adesao)
        try:
            cliente = cliente_service.criar(_cliente_da_adesao(adesao))
        except ErroCliente as erro:
            raise ErroDeNegocio(code=erro.code, message=erro.message, status=erro.status) from erro

        aprovada = self.atualizar(adesao_id, AdesaoUpdate(status=StatusAdesao.aprovada))
        return aprovada, cliente.id

    def recusar(self, adesao_id: int) -> Adesao:
        """Recusa a adesao (ex.: fora da area atendida)."""

        self._exigir_enviada(self.buscar_por_id(adesao_id))
        return self.atualizar(adesao_id, AdesaoUpdate(status=StatusAdesao.recusada))


# Uma unica instancia compartilhada por toda a aplicacao.
adesao_service = AdesaoService(
    adesao_repository
)
