"""
Camada de Servico, SimulacaoService.
"""
from app.domain.simulacao import Simulacao, SimulacaoCreate
from app.repositories.simulacao_repository import SimulacaoRepository,simulacao_repository

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
class SimulacaoService:
    def __init__(self, repository: SimulacaoRepository) -> None:
        self._repository = repository
    def listar(self) -> list[Simulacao]:
        return self._repository.listar()
    def buscar_por_id(self, simulacao_id: int) -> Simulacao:
        simulacao = self._repository.buscar_por_id(simulacao_id)
        if simulacao is None:
            raise ErroDeNegocio(
                code="RECURSO_NAO_ENCONTRADO",
                message=f"Simulacao com id {simulacao_id} nao foi encontrada.",
                status=404,
            )
        return simulacao
    def criar(self, dados: SimulacaoCreate) -> Simulacao:
        return self._repository.criar(dados)
    def remover(self, simulacao_id: int) -> None:
        removida = self._repository.remover(simulacao_id)
        if not removida:
            raise ErroDeNegocio(
                code="RECURSO_NAO_ENCONTRADO",
                message=f"Simulacao com id {simulacao_id} nao foi encontrada.",
                status=404,
            )
# Uma unica instancia compartilhada por toda a aplicacao.
simulacao_service = SimulacaoService(simulacao_repository)