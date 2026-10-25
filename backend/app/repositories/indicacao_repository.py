"""
Camada de Repositorio para Indicacoes.
"""
from typing import List, Optional

from app.domain.indicacao import Indicacao, IndicacaoCreate, StatusIndicacao


class IndicacaoRepository:
    """Repositorio em memoria para indicacoes."""

    def __init__(self):
        self._indicacoes: List[Indicacao] = []
        self._next_id = 1

    def criar(self, dados: IndicacaoCreate) -> Indicacao:
        indicacao = Indicacao(
            id=self._next_id,
            cliente_id=dados.cliente_id,
            nome=dados.nome,
            contato=dados.contato,
            situacao=StatusIndicacao.pendente,
            bonus=50.0
        )

        self._indicacoes.append(indicacao)
        self._next_id += 1

        return indicacao

    def buscar_por_id(self, indicacao_id: int) -> Optional[Indicacao]:
        for indicacao in self._indicacoes:
            if indicacao.id == indicacao_id:
                return indicacao

        return None

    def listar_por_cliente(self, cliente_id: int) -> List[Indicacao]:
        return [
            indicacao
            for indicacao in self._indicacoes
            if indicacao.cliente_id == cliente_id
        ]

    def buscar_por_contato(self, contato: str) -> Optional[Indicacao]:
        for indicacao in self._indicacoes:
            if indicacao.contato.lower() == contato.lower():
                return indicacao

        return None

    def excluir(self, indicacao_id: int) -> bool:
        indicacao = self.buscar_por_id(indicacao_id)

        if indicacao is None:
            return False

        self._indicacoes.remove(indicacao)
        return True


indicacao_repository = IndicacaoRepository() 