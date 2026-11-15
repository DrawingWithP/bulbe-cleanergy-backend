"""
Camada de Servico, IndicacaoService.
"""

from app.domain.indicacao import (
    Indicacao,
    IndicacaoCreate,
    StatusIndicacao,
)
from app.repositories.cliente_repository import (
    ClienteRepository,
    cliente_repository,
)
from app.repositories.indicacao_repository import (
    IndicacaoRepository,
    indicacao_repository,
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


class IndicacaoService:
    def __init__(
        self,
        repository: IndicacaoRepository,
        clientes: ClienteRepository = cliente_repository,
    ) -> None:
        self._repository = repository
        self._clientes = clientes

    def _validar_cliente(
        self,
        cliente_id: str,
    ) -> None:
        if self._clientes.buscar_por_id(cliente_id) is None:
            raise ErroDeNegocio(
                code="RECURSO_NAO_ENCONTRADO",
                message=(
                    f"Cliente com id '{cliente_id}' "
                    "nao foi encontrado."
                ),
                status=404,
            )

    def criar(
        self,
        dados: IndicacaoCreate,
    ) -> Indicacao:
        """
        Cria uma nova indicacao para um cliente existente.
        """

        self._validar_cliente(dados.cliente_id)

        existente = self._repository.buscar_por_contato(
            dados.contato
        )

        if existente is not None:
            raise ErroDeNegocio(
                code="INDICACAO_DUPLICADA",
                message=(
                    "Esta pessoa ja possui uma "
                    "indicacao cadastrada."
                ),
                status=409,
            )

        return self._repository.criar(dados)

    def buscar_por_id(
        self,
        indicacao_id: int,
    ) -> Indicacao:
        """
        Busca uma indicacao pelo ID.
        """

        indicacao = self._repository.buscar_por_id(
            indicacao_id
        )

        if indicacao is None:
            raise ErroDeNegocio(
                code="RECURSO_NAO_ENCONTRADO",
                message=(
                    f"Indicacao com id {indicacao_id} "
                    "nao foi encontrada."
                ),
                status=404,
            )

        return indicacao

    def listar_por_cliente(
        self,
        cliente_id: str,
    ) -> list[Indicacao]:
        """
        Lista as indicacoes de um cliente.
        """

        self._validar_cliente(cliente_id)

        return self._repository.listar_por_cliente(
            cliente_id
        )

    def excluir(
        self,
        indicacao_id: int,
    ) -> None:
        """
        Exclui uma indicacao caso ela ainda esteja pendente.
        """

        indicacao = self.buscar_por_id(indicacao_id)

        if indicacao.situacao != StatusIndicacao.pendente:
            raise ErroDeNegocio(
                code="INDICACAO_NAO_PODE_SER_EXCLUIDA",
                message=(
                    "A indicacao nao pode ser excluida "
                    "porque ja foi concluida."
                ),
                status=409,
            )

        removida = self._repository.excluir(
            indicacao_id
        )

        if removida is False:
            raise ErroDeNegocio(
                code="RECURSO_NAO_ENCONTRADO",
                message=(
                    f"Indicacao com id {indicacao_id} "
                    "nao foi encontrada."
                ),
                status=404,
            )


indicacao_service = IndicacaoService(
    indicacao_repository
)
