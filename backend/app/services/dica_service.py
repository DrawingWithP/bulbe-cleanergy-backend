"""
Camada de Servico, DicaService.
"""
from app.domain.dica import Dica, DicaCreate, DicaUpdate
from app.repositories.dica_repository import DicaRepository, dica_repository


class ErroDeNegocio(Exception):
    """
    Erro de negocio com formato padronizado (Aula 10):
    code, message e status.
    """
    def __init__(self, code: str, message: str, status: int) -> None:
        self.code = code
        self.message = message
        self.status = status
        super().__init__(message)


class DicaService:
    def __init__(self, repository: DicaRepository) -> None:
        self._repository = repository

    def listar(self) -> list[Dica]:
        return self._repository.listar()

    def buscar_por_id(self, dica_id: int) -> Dica:
        dica = self._repository.buscar_por_id(dica_id)
        if dica is None:
            raise ErroDeNegocio(
                code="RECURSO_NAO_ENCONTRADO",
                message=f"Dica com id {dica_id} nao foi encontrada.",
                status=404,
            )
        return dica

    def criar(self, dados: DicaCreate) -> Dica:
        return self._repository.criar(dados)

    def atualizar(self, dica_id: int, dados: DicaUpdate) -> Dica:
        dica_atualizada = self._repository.atualizar(dica_id, dados)
        if dica_atualizada is None:
            raise ErroDeNegocio(
                code="RECURSO_NAO_ENCONTRADO",
                message=f"Dica com id {dica_id} nao foi encontrada.",
                status=404,
            )
        return dica_atualizada

    def remover(self, dica_id: int) -> None:
        removido = self._repository.remover(dica_id)
        if not removido:
            raise ErroDeNegocio(
                code="RECURSO_NAO_ENCONTRADO",
                message=f"Dica com id {dica_id} nao foi encontrada.",
                status=404,
            )


dica_service = DicaService(dica_repository)
