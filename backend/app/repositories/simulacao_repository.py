"""
Camada de Persistencia, SimulacaoRepository.
"""
from datetime import date
from app.domain.simulacao import Simulacao, SimulacaoCreate
class SimulacaoRepository:
    def __init__(self) -> None:
        self._simulacoes: dict[int, Simulacao] = {}
        self._proximo_id: int = 1
    def listar(self) -> list[Simulacao]:
        return list(self._simulacoes.values())
    def buscar_por_id(self, simulacao_id: int) -> Simulacao | None:
        return self._simulacoes.get(simulacao_id)
    def criar(self, dados: SimulacaoCreate) -> Simulacao:
        simulacao = Simulacao(
            id=self._proximo_id,
            data_ativacao=date.today(),
            **dados.model_dump(),
        )
        self._simulacoes[simulacao.id] = simulacao
        self._proximo_id += 1
        return simulacao
    def remover(self, simulacao_id: int) -> bool:
        if simulacao_id not in self._simulacoes:
            return False
        del self._simulacoes[simulacao_id]
        return True
# Uma unica instancia compartilhada por toda a aplicacao.
simulacao_repository = SimulacaoRepository()