"""
Camada de Servico, UsinaService.
"""
from app.domain.usina import Usina, UsinaCreate, UsinaUpdate
from app.repositories.usina_repository import UsinaRepository,usina_repository

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
class UsinaService:
    def __init__(self, repository: UsinaRepository) -> None:
        self._repository = repository
    def listar(self) -> list[Usina]:
        return self._repository.listar()
    def buscar_por_id(self, usina_id: int) -> Usina:
        usina = self._repository.buscar_por_id(usina_id)
        if usina is None:
            raise ErroDeNegocio(
                code="RECURSO_NAO_ENCONTRADO",
                message=f"Usina com id {usina_id} nao foi encontrada.",
                status=404,
            )
        return usina
    def criar(self, dados: UsinaCreate) -> Usina:
        return self._repository.criar(dados)
    def atualizar(self, usina_id: int, dados: UsinaUpdate) -> Usina:
        usina_atualizada = self._repository.atualizar(usina_id, dados)
        if usina_atualizada is None:
            raise ErroDeNegocio(
                code="RECURSO_NAO_ENCONTRADO",
                message=f"Usina com id {usina_id} nao foi encontrada.",
                status=404,
            )
        return usina_atualizada
    def remover(self, usina_id: int) -> None:
        removida = self._repository.remover(usina_id)
        if not removida:
            raise ErroDeNegocio(
                code="RECURSO_NAO_ENCONTRADO",
                message=f"Usina com id {usina_id} nao foi encontrada.",
                status=404,
            )
# Uma unica instancia compartilhada por toda a aplicacao.
usina_service = UsinaService(usina_repository)