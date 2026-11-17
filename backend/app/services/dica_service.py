"""
Camada de Servico, DicaService.
"""

from app.domain.dica import (
    TAMANHO_VITRINE,
    Dica,
    DicaCreate,
    DicaUpdate,
)
from app.repositories.dica_repository import (
    DicaRepository,
    dica_repository,
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


class DicaService:
    def __init__(
        self,
        repository: DicaRepository,
    ) -> None:
        self._repository = repository

    def listar(self, todas: bool = False) -> list[Dica]:
        """
        Sem `todas`: as dicas da vitrine do app, na ordem do carrossel.
        Se a vitrine ainda nao foi montada, todas as dicas (compatibilidade).
        Com `todas`: o acervo inteiro (vitrine primeiro, na ordem).
        """

        dicas = self._repository.listar()
        vitrine = sorted(
            (d for d in dicas if d.em_exibicao),
            key=lambda d: (d.ordem or 0, d.id),
        )
        if todas:
            return vitrine + [d for d in dicas if not d.em_exibicao]
        return vitrine or dicas

    def definir_vitrine(self, ids: list[int]) -> list[Dica]:
        """Troca as 5 dicas do app de uma vez (ordem = ordem da lista)."""

        if len(ids) != TAMANHO_VITRINE or len(set(ids)) != TAMANHO_VITRINE:
            raise ErroDeNegocio(
                code="VITRINE_INVALIDA",
                message=f"A vitrine precisa de exatamente {TAMANHO_VITRINE} dicas diferentes.",
                status=422,
            )
        existentes = {d.id for d in self._repository.listar()}
        faltando = [dica_id for dica_id in ids if dica_id not in existentes]
        if faltando:
            raise ErroDeNegocio(
                code="VITRINE_INVALIDA",
                message=f"Dica(s) inexistente(s): {', '.join(map(str, faltando))}.",
                status=422,
            )
        self._repository.definir_vitrine(ids)
        return self.listar()

    def buscar_por_id(
        self,
        dica_id: int,
    ) -> Dica:
        """
        Busca uma dica pelo ID.
        """

        dica = self._repository.buscar_por_id(dica_id)

        if dica is None:
            raise ErroDeNegocio(
                code="RECURSO_NAO_ENCONTRADO",
                message=(
                    f"Dica com id {dica_id} "
                    "nao foi encontrada."
                ),
                status=404,
            )

        return dica

    def criar(
        self,
        dados: DicaCreate,
    ) -> Dica:
        """
        Cria uma nova dica.
        """

        return self._repository.criar(dados)

    def atualizar(
        self,
        dica_id: int,
        dados: DicaUpdate,
    ) -> Dica:
        """
        Atualiza uma dica existente.
        """

        dica_atualizada = self._repository.atualizar(
            dica_id,
            dados,
        )

        if dica_atualizada is None:
            raise ErroDeNegocio(
                code="RECURSO_NAO_ENCONTRADO",
                message=(
                    f"Dica com id {dica_id} "
                    "nao foi encontrada."
                ),
                status=404,
            )

        return dica_atualizada

    def remover(
        self,
        dica_id: int,
    ) -> None:
        """
        Remove uma dica pelo ID. Dica na vitrine precisa ser trocada antes,
        para o app continuar com 5 dicas.
        """

        if self.buscar_por_id(dica_id).em_exibicao:
            raise ErroDeNegocio(
                code="DICA_NA_VITRINE",
                message="Tire a dica da vitrine do app antes de remove-la.",
                status=409,
            )

        removido = self._repository.remover(dica_id)

        if not removido:
            raise ErroDeNegocio(
                code="RECURSO_NAO_ENCONTRADO",
                message=(
                    f"Dica com id {dica_id} "
                    "nao foi encontrada."
                ),
                status=404,
            )


dica_service = DicaService(dica_repository)
