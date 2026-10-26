"""
Camada de Serviço, CupomService (regras de negócio para US-03, US-22 e US-23).
"""
from datetime import datetime, timezone

from app.domain.cupom import Cupom, CupomListaPaginada, CupomUpdate, SituacaoCupom
from app.repositories.cliente_repository import cliente_repository
from app.repositories.cupom_repository import CupomRepository, cupom_repository


class ErroDeNegocio(Exception):
    def __init__(self, code: str, message: str, status: int) -> None:
        self.code = code
        self.message = message
        self.status = status
        super().__init__(message)


class CupomService:
    def __init__(self, repository: CupomRepository) -> None:
        self._repository = repository

    def listar_por_cliente(
        self,
        cliente_id: str,
        page: int = 1,
        limit: int = 20,
        situacao: SituacaoCupom | None = None,
    ) -> CupomListaPaginada:
        """US-03: Lista os cupons do cliente."""
        if not cliente_repository.buscar_por_id(cliente_id):
            raise ErroDeNegocio(
                code="RECURSO_NAO_ENCONTRADO",
                message=f"Cliente com id '{cliente_id}' não foi encontrado.",
                status=404,
            )

        if page < 1 or limit < 1 or limit > 100:
            raise ErroDeNegocio(
                code="PARAMETROS_INVALIDOS",
                message="Parâmetros de paginação inválidos.",
                status=400,
            )

        cupons, total = self._repository.listar_por_cliente(cliente_id, page, limit, situacao)
        return CupomListaPaginada(data=cupons, page=page, total=total)

    def buscar_por_id(self, cupom_id: str) -> Cupom:
        """US-22: Retorna dados detalhados de um cupom específico."""
        cupom = self._repository.buscar_por_id(cupom_id)
        if not cupom:
            raise ErroDeNegocio(
                code="RECURSO_NAO_ENCONTRADO",
                message=f"Cupom com id '{cupom_id}' não foi encontrado.",
                status=404,
            )
        return cupom

    def atualizar_situacao(self, cupom_id: str, dados: CupomUpdate) -> Cupom:
        """US-23: Atualiza situação do cupom (salvo ou usado)."""
        cupom = self.buscar_por_id(cupom_id)

        if dados.situacao not in [SituacaoCupom.salvo, SituacaoCupom.usado]:
            raise ErroDeNegocio(
                code="SITUACAO_INVALIDA",
                message="Apenas é permitido alterar a situação para 'salvo' ou 'usado'.",
                status=400,
            )

        if cupom.situacao == SituacaoCupom.usado and dados.situacao != SituacaoCupom.usado:
            raise ErroDeNegocio(
                code="CUPOM_JA_UTILIZADO",
                message="Um cupom já utilizado não pode ter sua situação alterada.",
                status=409,
            )

        cupom.situacao = dados.situacao
        if dados.situacao == SituacaoCupom.usado:
            cupom.usado_em = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        return self._repository.atualizar(cupom)

    def descartar(self, cupom_id: str) -> None:
        """Descarta logicamente um cupom da carteira do cliente."""
        removido = self._repository.descartar(cupom_id)
        if not removido:
            raise ErroDeNegocio(
                code="RECURSO_NAO_ENCONTRADO",
                message=f"Cupom com id '{cupom_id}' não foi encontrado.",
                status=404,
            )


cupom_service = CupomService(cupom_repository)
