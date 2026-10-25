from typing import List

from app.domain.indicacao import Indicacao, IndicacaoCreate, StatusIndicacao
from app.repositories.indicacao_repository import indicacao_repository


class IndicacaoNaoEncontradaError(Exception):
    pass


class IndicacaoDuplicadaError(Exception):
    pass


class IndicacaoNaoPodeSerExcluidaError(Exception):
    pass


class IndicacaoService:

    def criar(self, dados: IndicacaoCreate) -> Indicacao:
        existente = indicacao_repository.buscar_por_contato(dados.contato)

        if existente is not None:
            raise IndicacaoDuplicadaError(
                "Esta pessoa ja possui uma indicacao cadastrada."
            )

        return indicacao_repository.criar(dados)

    def buscar_por_id(self, indicacao_id: int) -> Indicacao:
        indicacao = indicacao_repository.buscar_por_id(indicacao_id)

        if indicacao is None:
            raise IndicacaoNaoEncontradaError(
                "Indicacao nao encontrada."
            )

        return indicacao

    def listar_por_cliente(self, cliente_id: int) -> List[Indicacao]:
        return indicacao_repository.listar_por_cliente(cliente_id)

    def excluir(self, indicacao_id: int) -> None:
        indicacao = self.buscar_por_id(indicacao_id)

        if indicacao.situacao != StatusIndicacao.pendente:
            raise IndicacaoNaoPodeSerExcluidaError(
                "A indicacao nao pode ser excluida porque ja foi concluida."
            )

        indicacao_repository.excluir(indicacao_id)


indicacao_service = IndicacaoService() 