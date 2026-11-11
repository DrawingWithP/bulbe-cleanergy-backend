"""
Camada de Servico, AdesaoService.
"""

import re

from app.domain.adesao import (
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
    ) -> "
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


# Uma unica instancia compartilhada por toda a aplicacao.
adesao_service = AdesaoService(
    adesao_repository
)
