"""
Camada de Servico, catalogo de cupons do Clube Bulbe (cadastro e sorteio).
"""

import random
import uuid

from app.core import relogio
from app.domain.cupom_catalogo import (
    CupomCatalogo,
    CupomCatalogoCreate,
    CupomCatalogoUpdate,
)
from app.repositories.cupom_catalogo_repository import (
    CupomCatalogoRepository,
    cupom_catalogo_repository,
)
from app.repositories.parceiro_repository import (
    ParceiroRepository,
    parceiro_repository,
)


class ErroDeNegocio(Exception):
    """
    Erro de negocio com formato padronizado:
    code, message e status.
    """

    def __init__(self, code: str, message: str, status: int) -> None:
        self.code = code
        self.message = message
        self.status = status
        super().__init__(message)


class CupomCatalogoService:
    def __init__(
        self,
        repository: CupomCatalogoRepository,
        parceiros: ParceiroRepository = parceiro_repository,
    ) -> None:
        self._repository = repository
        self._parceiros = parceiros

    def _validar_parceiro(self, parceiro_id: str) -> None:
        if self._parceiros.buscar_por_id(parceiro_id) is None:
            raise ErroDeNegocio(
                code="PARCEIRO_NAO_ENCONTRADO",
                message=f"Parceiro com id '{parceiro_id}' nao foi encontrado.",
                status=422,
            )

    def listar(
        self,
        parceiro_id: str | None = None,
        apenas_ativos: bool = False,
    ) -> list[CupomCatalogo]:
        return self._repository.listar(parceiro_id, apenas_ativos)

    def buscar_por_id(self, modelo_id: str) -> CupomCatalogo:
        modelo = self._repository.buscar_por_id(modelo_id)
        if modelo is None:
            raise ErroDeNegocio(
                code="RECURSO_NAO_ENCONTRADO",
                message=f"Cupom do catalogo com id '{modelo_id}' nao foi encontrado.",
                status=404,
            )
        return modelo

    def criar(self, dados: CupomCatalogoCreate) -> CupomCatalogo:
        self._validar_parceiro(dados.parceiro_id)
        modelo = CupomCatalogo(
            id=str(uuid.uuid4()),
            criado_em=relogio.instante_iso(),
            **dados.model_dump(),
        )
        return self._repository.salvar(modelo)

    def atualizar(self, modelo_id: str, dados: CupomCatalogoUpdate) -> CupomCatalogo:
        atual = self.buscar_por_id(modelo_id)
        alteracoes = dados.model_dump(exclude_unset=True, exclude_none=True)
        if "parceiro_id" in alteracoes:
            self._validar_parceiro(alteracoes["parceiro_id"])
        novo = atual.model_copy(
            update={**alteracoes, "atualizado_em": relogio.instante_iso()}
        )
        return self._repository.salvar(novo)

    def remover(self, modelo_id: str) -> None:
        if not self._repository.remover(modelo_id):
            raise ErroDeNegocio(
                code="RECURSO_NAO_ENCONTRADO",
                message=f"Cupom do catalogo com id '{modelo_id}' nao foi encontrado.",
                status=404,
            )

    def sortear(
        self,
        evitar_modelo_id: str | None = None,
        sorteio: random.Random | None = None,
    ) -> CupomCatalogo | None:
        """
        Sorteia um modelo ativo (de parceiro ativo), com chance proporcional
        ao peso. Evita repetir `evitar_modelo_id` (o cupom da semana anterior do
        mesmo cliente) quando houver outra opcao. None se o catalogo estiver vazio.
        """
        ativos = self._repository.listar(apenas_ativos=True)
        if not ativos:
            return None
        opcoes = [m for m in ativos if m.id != evitar_modelo_id] or ativos
        gerador = sorteio or random.SystemRandom()
        return gerador.choices(opcoes, weights=[m.peso for m in opcoes], k=1)[0]


cupom_catalogo_service = CupomCatalogoService(cupom_catalogo_repository)
