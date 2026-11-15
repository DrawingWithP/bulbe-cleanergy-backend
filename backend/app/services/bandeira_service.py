"""
Camada de Servico, BandeiraService (RF-03).
"""

from app.domain.bandeira import (
    ADICIONAL_POR_KWH,
    BANDEIRA_PADRAO,
    BandeiraMes,
    BandeiraTarifaria,
    mes_referencia_atual,
    mes_referencia_valido,
)
from app.repositories.bandeira_repository import (
    BandeiraRepository,
    bandeira_repository,
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


class BandeiraService:
    def __init__(
        self,
        repository: BandeiraRepository,
    ) -> None:
        self._repository = repository

    @staticmethod
    def _validar_mes(mes_referencia: str) -> None:
        if not mes_referencia_valido(mes_referencia):
            raise ErroDeNegocio(
                code="MES_REFERENCIA_INVALIDO",
                message=(
                    "O mes de referencia deve estar "
                    "no formato AAAA-MM."
                ),
                status=422,
            )

    def listar(self) -> list[BandeiraMes]:
        """Lista os meses cadastrados, do mais recente ao mais antigo."""

        return self._repository.listar()

    def obter(
        self,
        mes_referencia: str | None = None,
    ) -> BandeiraMes:
        """
        Bandeira de um mes (padrao: mes atual).

        Mes sem cadastro usa a bandeira verde, sem acrescimo,
        e devolve definida=False.
        """

        mes = mes_referencia or mes_referencia_atual()
        self._validar_mes(mes)

        registro = self._repository.buscar(mes)

        if registro is not None:
            return registro

        return BandeiraMes(
            mes_referencia=mes,
            bandeira=BANDEIRA_PADRAO,
            adicional_por_kwh=ADICIONAL_POR_KWH[BANDEIRA_PADRAO],
            definida=False,
            atualizado_em=None,
        )

    def definir(
        self,
        mes_referencia: str,
        bandeira: BandeiraTarifaria,
    ) -> BandeiraMes:
        """Cadastra ou altera a bandeira de um mes."""

        self._validar_mes(mes_referencia)

        return self._repository.salvar(
            mes_referencia,
            bandeira,
        )


bandeira_service = BandeiraService(
    bandeira_repository
)
