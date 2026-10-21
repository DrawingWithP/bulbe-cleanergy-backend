"""
Camada de Servico, AdesaoService.
"""
from app.domain.adesao import Adesao, AdesaoCreate, AdesaoUpdate
from app.repositories.adesao_repository import AdesaoRepository,adesao_repository

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
class AdesaoService:
    def __init__(self, repository: AdesaoRepository) -> None:
        self._repository = repository
    def listar(self) -> list[Adesao]:
        return self._repository.listar()
    def buscar_por_id(self, adesao_id: int) -> Adesao:
        adesao = self._repository.buscar_por_id(adesao_id)
        if adesao is None:
            raise ErroDeNegocio(
                code="RECURSO_NAO_ENCONTRADO",
                message=f"Adesao com id {adesao_id} nao foi encontrada.",
                status=404,
            )
        return adesao
    def criar(self, dados: AdesaoCreate) -> Adesao:
        return self._repository.criar(dados)
    def atualizar(self, adesao_id: int, dados: AdesaoUpdate) -> Adesao:
        adesao_atualizada = self._repository.atualizar(adesao_id, dados)
        if adesao_atualizada is None:
            raise ErroDeNegocio(
                code="RECURSO_NAO_ENCONTRADO",
                message=f"Adesao com id {adesao_id} nao foi encontrada.",
                status=404,
            )
        return adesao_atualizada
    def remover(self, adesao_id: int) -> None:
        removida = self._repository.remover(adesao_id)
        if not removida:
            raise ErroDeNegocio(
                code="RECURSO_NAO_ENCONTRADO",
                message=f"Adesao com id {adesao_id} nao foi encontrada.",
                status=404,
            )
# Uma unica instancia compartilhada por toda a aplicacao.
adesao_service = AdesaoService(adesao_repository)