"""
Camada de Servico, SimulacaoService.
"""

from app.domain.bandeira import (
    ADICIONAL_POR_KWH,
    TARIFA_MEDIA_KWH,
    BandeiraTarifaria,
)
from app.domain.indicacao import BONUS_PADRAO_INDICACAO
from app.domain.simulacao import (
    Simulacao,
    SimulacaoCalculada,
    SimulacaoCreate,
)
from app.repositories.cliente_repository import (
    ClienteRepository,
    cliente_repository,
)
from app.repositories.simulacao_repository import (
    SimulacaoRepository,
    simulacao_repository,
)
from app.services.bandeira_service import (
    BandeiraService,
    bandeira_service,
)


def calcular_economia(
    valor_atual: float,
    valor_proposto: float,
    periodo_meses: int,
    indicacoes: int,
    bandeira: BandeiraTarifaria,
) -> tuple[float, float]:
    """
    Economia mensal e total da simulacao (RF-03).

    - O desconto da Bulbe e a diferenca entre o valor atual e o proposto
      (o app envia valor_proposto = 85% do valor atual, ou seja, 15%).
    - O consumo e estimado pela tarifa media; a bandeira acrescenta
      ADICIONAL_POR_KWH a cada kWh, entao a conta projetada sobe e o
      desconto rende mais em reais.
    - Cada indicacao vale o bonus padrao (R$ 50), uma unica vez.

    Com a bandeira verde, o resultado e o mesmo calculo do app:
    economia_mensal = 15% da conta.
    """

    desconto = 1 - (valor_proposto / valor_atual)
    desconto = min(max(desconto, 0.0), 1.0)

    consumo_kwh = valor_atual / TARIFA_MEDIA_KWH
    conta_projetada = valor_atual + consumo_kwh * ADICIONAL_POR_KWH[bandeira]

    economia_mensal = round(conta_projetada * desconto, 2)
    economia_total = round(
        economia_mensal * periodo_meses
        + indicacoes * BONUS_PADRAO_INDICACAO,
        2,
    )

    return economia_mensal, economia_total


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


class SimulacaoService:
    def __init__(
        self,
        repository: SimulacaoRepository,
        bandeiras: BandeiraService = bandeira_service,
        clientes: ClienteRepository = cliente_repository,
    ) -> None:
        self._repository = repository
        self._bandeiras = bandeiras
        self._clientes = clientes

    def listar(self) -> list[Simulacao]:
        """
        Lista todas as simulacoes cadastradas.
        """

        return self._repository.listar()

    def buscar_por_id(
        self,
        simulacao_id: int,
    ) -> Simulacao:
        """
        Busca uma simulacao pelo ID.
        """

        simulacao = self._repository.buscar_por_id(
            simulacao_id
        )

        if simulacao is None:
            raise ErroDeNegocio(
                code="RECURSO_NAO_ENCONTRADO",
                message=(
                    f"Simulacao com id {simulacao_id} "
                    "nao foi encontrada."
                ),
                status=404,
            )

        return simulacao

    def criar(
        self,
        dados: SimulacaoCreate,
    ) -> Simulacao:
        """
        Cria uma nova simulacao, com a economia calculada
        pela bandeira informada ou pela vigente no mes.
        """

        if (
            dados.cliente_id is not None
            and self._clientes.buscar_por_id(dados.cliente_id) is None
        ):
            raise ErroDeNegocio(
                code="RECURSO_NAO_ENCONTRADO",
                message=(
                    f"Cliente com id '{dados.cliente_id}' "
                    "nao foi encontrado."
                ),
                status=404,
            )

        bandeira = (
            dados.bandeira
            or self._bandeiras.obter().bandeira
        )

        economia_mensal, economia_total = calcular_economia(
            dados.valor_atual,
            dados.valor_proposto,
            dados.periodo_meses,
            dados.indicacoes,
            bandeira,
        )

        return self._repository.criar(
            SimulacaoCalculada(
                **dados.model_dump(exclude={"bandeira"}),
                bandeira=bandeira,
                economia_mensal=economia_mensal,
                economia_total=economia_total,
            )
        )

    def remover(
        self,
        simulacao_id: int,
    ) -> None:
        """
        Remove uma simulacao pelo ID.
        """

        removida = self._repository.remover(
            simulacao_id
        )

        if not removida:
            raise ErroDeNegocio(
                code="RECURSO_NAO_ENCONTRADO",
                message=(
                    f"Simulacao com id {simulacao_id} "
                    "nao foi encontrada."
                ),
                status=404,
            )


# Uma unica instancia compartilhada por toda a aplicacao.
simulacao_service = SimulacaoService(
    simulacao_repository
)
