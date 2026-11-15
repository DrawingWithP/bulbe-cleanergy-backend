"""
Camada de Serviço, CupomService
(regras de negócio para US-03, US-22 e US-23).
"""

from datetime import date

from app.core import relogio
from app.domain.cupom import (
    Cupom,
    CupomListaPaginada,
    CupomUpdate,
    SituacaoCupom,
)
from app.repositories.cliente_repository import (
    ClienteRepository,
    cliente_repository,
)
from app.repositories.cupom_repository import (
    CupomRepository,
    cupom_repository,
)


class ErroDeNegocio(Exception):
    """
    Erro de negócio com formato padronizado:
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


class CupomService:
    def __init__(
        self,
        repository: CupomRepository,
        clientes: ClienteRepository = cliente_repository,
    ) -> None:
        self._repository = repository
        self._clientes = clientes

    def _validar_cliente(self, cliente_id: str) -> None:
        """
        Verifica se o cliente informado existe.
        """

        cliente = self._clientes.buscar_por_id(cliente_id)

        if not cliente:
            raise ErroDeNegocio(
                code="RECURSO_NAO_ENCONTRADO",
                message=(
                    f"Cliente com id '{cliente_id}' "
                    "não foi encontrado."
                ),
                status=404,
            )

    def _atualizar_validade(self, cupom: Cupom) -> Cupom:
        """
        Recalcula os dias restantes pelo relogio da API e marca como
        expirado o cupom ativo/salvo que passou da validade.
        """

        if cupom.situacao not in (SituacaoCupom.ativo, SituacaoCupom.salvo):
            return cupom

        dias = (date.fromisoformat(cupom.valido_ate) - relogio.hoje()).days
        situacao = SituacaoCupom.expirado if dias < 0 else cupom.situacao
        dias = max(dias, 0)

        if (situacao, dias) != (cupom.situacao, cupom.dias_restantes):
            cupom.situacao = situacao
            cupom.dias_restantes = dias
            cupom = self._repository.atualizar(cupom)

        return cupom

    def _atualizar_validade_do_cliente(self, cliente_id: str) -> None:
        pagina = 1
        while True:
            cupons, total = self._repository.listar_por_cliente(
                cliente_id, pagina, 100, None
            )
            for cupom in cupons:
                self._atualizar_validade(cupom)
            if pagina * 100 >= total or not cupons:
                return
            pagina += 1

    def listar_por_cliente(
        self,
        cliente_id: str,
        page: int = 1,
        limit: int = 20,
        situacao: SituacaoCupom | None = None,
    ) -> CupomListaPaginada:
        """
        US-03: Lista os cupons do cliente.
        """

        self._validar_cliente(cliente_id)
        self._atualizar_validade_do_cliente(cliente_id)

        if page < 1:
            raise ErroDeNegocio(
                code="PARAMETROS_INVALIDOS",
                message=(
                    "O número da página deve ser "
                    "maior ou igual a 1."
                ),
                status=400,
            )

        if limit < 1 or limit > 100:
            raise ErroDeNegocio(
                code="PARAMETROS_INVALIDOS",
                message="O limite deve estar entre 1 e 100.",
                status=400,
            )

        cupons, total = self._repository.listar_por_cliente(
            cliente_id,
            page,
            limit,
            situacao,
        )

        return CupomListaPaginada(
            data=cupons,
            page=page,
            total=total,
        )

    def buscar_por_id(
        self,
        cupom_id: str,
    ) -> Cupom:
        """
        US-22: Retorna os dados detalhados
        de um cupom específico.
        """

        cupom = self._repository.buscar_por_id(cupom_id)

        if not cupom:
            raise ErroDeNegocio(
                code="RECURSO_NAO_ENCONTRADO",
                message=(
                    f"Cupom com id '{cupom_id}' "
                    "não foi encontrado."
                ),
                status=404,
            )

        return self._atualizar_validade(cupom)

    def atualizar_situacao(
        self,
        cupom_id: str,
        dados: CupomUpdate,
    ) -> Cupom:
        """
        US-23: Atualiza a situação do cupom
        para salvo ou usado.
        """

        cupom = self.buscar_por_id(cupom_id)

        situacoes_permitidas = {
            SituacaoCupom.salvo,
            SituacaoCupom.usado,
        }

        if dados.situacao not in situacoes_permitidas:
            raise ErroDeNegocio(
                code="SITUACAO_INVALIDA",
                message=(
                    "Apenas é permitido alterar a situação "
                    "para 'salvo' ou 'usado'."
                ),
                status=400,
            )

        if cupom.situacao == SituacaoCupom.expirado:
            raise ErroDeNegocio(
                code="CUPOM_EXPIRADO",
                message="Este cupom passou da validade.",
                status=409,
            )

        if (
            cupom.situacao == SituacaoCupom.usado
            and dados.situacao != SituacaoCupom.usado
        ):
            raise ErroDeNegocio(
                code="CUPOM_JA_UTILIZADO",
                message=(
                    "Um cupom já utilizado não pode ter "
                    "sua situação alterada."
                ),
                status=409,
            )

        cupom.situacao = dados.situacao

        if dados.situacao == SituacaoCupom.usado:
            if cupom.usado_em is None:
                cupom.usado_em = relogio.agora().strftime("%Y-%m-%dT%H:%M:%SZ")

        return self._repository.atualizar(cupom)

    def descartar(
        self,
        cupom_id: str,
    ) -> None:
        """
        Descarta logicamente um cupom da carteira do cliente.
        """

        removido = self._repository.descartar(cupom_id)

        if not removido:
            raise ErroDeNegocio(
                code="RECURSO_NAO_ENCONTRADO",
                message=(
                    f"Cupom com id '{cupom_id}' "
                    "não foi encontrado."
                ),
                status=404,
            )


cupom_service = CupomService(cupom_repository)
