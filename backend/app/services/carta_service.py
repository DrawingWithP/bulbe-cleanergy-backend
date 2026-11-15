"""
Camada de Serviço, CartaService e Clube Bulbe
(US-18, US-19, US-20 e US-21).
"""

from datetime import timedelta
import math
import uuid

from app.core import relogio
from app.domain.carta import (
    AberturaCartaResponse,
    Carta,
    CartaListaPaginada,
    ClubeSituacaoResponse,
    ProximaCartaInfo,
    SituacaoCarta,
    TipoCarta,
)
from app.domain.cupom import (
    Cupom,
    ParceiroResumoCupom,
    SituacaoCupom,
)
from app.repositories.carta_repository import (
    CartaRepository,
    carta_repository,
)
from app.repositories.cliente_repository import (
    ClienteRepository,
    cliente_repository,
)
from app.repositories.cupom_repository import (
    CupomRepository,
    cupom_repository,
)


META_SEQUENCIA = 5
INTERVALO_CARTAS_DIAS = 7
VALIDADE_CUPOM_DIAS = 14
DIAS_PROXIMA_CARTA = 4

PARCEIRO_PADRAO_ID = "3e5a7c19-8b24-4d60-a1f3-7c9e2b5d8a06"
PARCEIRO_PADRAO_NOME = "Livelo"
PARCEIRO_PADRAO_CATEGORIA = "Programa de pontos"

# Carta especial (5 semanas seguidas): sempre R$ 50 de desconto na fatura.
BONUS_ESPECIAL_VALOR = 50
PARCEIRO_BULBE = ParceiroResumoCupom(
    id="bulbe",
    nome="Bulbe Energia",
    categoria="Energia",
)


class ErroDeNegocio(Exception):
    def __init__(self, code: str, message: str, status: int) -> None:
        self.code = code
        self.message = message
        self.status = status
        super().__init__(message)


class CartaService:
    def __init__(
        self,
        repository: CartaRepository,
        clientes: ClienteRepository = cliente_repository,
        cupons: CupomRepository = cupom_repository,
    ) -> None:
        self._repository = repository
        self._clientes = clientes
        self._cupons = cupons

    def _validar_cliente(self, cliente_id: str) -> None:
        """Verifica se o cliente informado existe."""

        cliente = self._clientes.buscar_por_id(cliente_id)

        if not cliente:
            raise ErroDeNegocio(
                code="RECURSO_NAO_ENCONTRADO",
                message=f"Cliente com id '{cliente_id}' não foi encontrado.",
                status=404,
            )

    def _sequencia(
        self,
        cliente_id: str,
        padrao: int = 0,
    ) -> int:
        """
        Retorna as semanas seguidas de ofensiva armazenadas
        no repositório.
        """

        sequencia = self._repository.obter_sequencia(cliente_id)

        if sequencia is None:
            return padrao

        return sequencia

    def _cartas_bloqueadas(
        self,
        cliente_id: str,
    ) -> list[Carta]:
        """Cartas agendadas (bloqueadas) que ainda nao foram abertas."""

        cartas, _ = self._repository.listar_por_cliente(
            cliente_id,
            1,
            100,
            SituacaoCarta.bloqueada,
        )

        return [carta for carta in cartas if carta.cupom_id is None]

    def _liberar_cartas(
        self,
        cliente_id: str,
    ) -> None:
        """
        A carta da semana nasce bloqueada com a data de liberacao;
        quando essa data chega (pelo relogio da API), ela fica disponivel.
        """

        agora = relogio.agora()

        for carta in self._cartas_bloqueadas(cliente_id):
            if relogio.ler_instante(carta.disponivel_em) <= agora:
                carta.situacao = SituacaoCarta.disponivel
                self._repository.atualizar(carta)

    def obter_situacao_clube(
        self,
        cliente_id: str,
    ) -> ClubeSituacaoResponse:
        """
        US-18: Retorna a situação do cliente no Clube Bulbe,
        incluindo ofensiva e status da próxima carta.
        """

        self._validar_cliente(cliente_id)
        self._liberar_cartas(cliente_id)

        carta_disponivel = (
            self._repository.buscar_disponivel_cliente(cliente_id)
        )

        sequencia = self._sequencia(cliente_id)
        agora = relogio.agora()
        agendadas = sorted(
            self._cartas_bloqueadas(cliente_id),
            key=lambda carta: carta.disponivel_em,
        )

        if carta_disponivel:
            proxima_carta = ProximaCartaInfo(
                carta_id=carta_disponivel.id,
                disponivel_em=carta_disponivel.disponivel_em,
                dias_restantes=0,
            )
        elif agendadas:
            # Proxima carta real: dias que faltam ate a data de liberacao.
            proxima = agendadas[0]
            faltam = relogio.ler_instante(proxima.disponivel_em) - agora
            proxima_carta = ProximaCartaInfo(
                carta_id=proxima.id,
                disponivel_em=proxima.disponivel_em,
                dias_restantes=max(
                    1,
                    math.ceil(faltam.total_seconds() / 86_400),
                ),
            )
        else:
            proxima_data = agora + timedelta(
                days=DIAS_PROXIMA_CARTA
            )

            proxima_carta = ProximaCartaInfo(
                carta_id="proxima-carta-agendada",
                disponivel_em=proxima_data.strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                ),
                dias_restantes=DIAS_PROXIMA_CARTA,
            )

        return ClubeSituacaoResponse(
            cliente_id=cliente_id,
            semanas_sequencia=sequencia,
            meta_sequencia=META_SEQUENCIA,
            carta_disponivel=(carta_disponivel is not None),
            bonus_especial_pendente=(
                sequencia >= META_SEQUENCIA
            ),
            proxima_carta=proxima_carta,
            intervalo_dias=INTERVALO_CARTAS_DIAS,
        )

    def listar_cartas_cliente(
        self,
        cliente_id: str,
        page: int = 1,
        limit: int = 20,
        situacao: SituacaoCarta | None = None,
    ) -> CartaListaPaginada:
        """
        US-19: Lista o histórico de cartas semanais do cliente.
        """

        self._validar_cliente(cliente_id)
        self._liberar_cartas(cliente_id)

        if page < 1:
            raise ErroDeNegocio(
                code="PAGINA_INVALIDA",
                message="O número da página deve ser maior ou igual a 1.",
                status=400,
            )

        if limit < 1 or limit > 100:
            raise ErroDeNegocio(
                code="LIMITE_INVALIDO",
                message="O limite deve estar entre 1 e 100.",
                status=400,
            )

        cartas, total = self._repository.listar_por_cliente(
            cliente_id,
            page,
            limit,
            situacao,
        )

        return CartaListaPaginada(
            data=cartas,
            page=page,
            total=total,
        )

    def buscar_por_id(self, carta_id: str) -> Carta:
        """
        US-20: Consulta os dados de uma carta específica.
        """

        carta = self._repository.buscar_por_id(carta_id)

        if not carta:
            raise ErroDeNegocio(
                code="RECURSO_NAO_ENCONTRADO",
                message=f"Carta com id '{carta_id}' não foi encontrada.",
                status=404,
            )

        return carta

    def abrir_carta(
        self,
        carta_id: str,
    ) -> AberturaCartaResponse:
        """
        US-21: Abre a carta semanal, gera a recompensa
        em cupom e avança a ofensiva.
        """

        carta = self.buscar_por_id(carta_id)
        self._liberar_cartas(carta.cliente_id)
        carta = self.buscar_por_id(carta_id)
        agora = relogio.agora()

        # Idempotência: se a carta já estiver aberta,
        # retorna o mesmo cupom anteriormente gerado.
        if (
            carta.situacao == SituacaoCarta.aberta
            and carta.cupom_id
        ):
            cupom_existente = self._cupons.buscar_por_id(
                carta.cupom_id
            )

            if cupom_existente:
                sequencia_atual = self._sequencia(
                    carta.cliente_id
                )

                proxima_data = agora + timedelta(
                    days=INTERVALO_CARTAS_DIAS
                )

                return AberturaCartaResponse(
                    carta_id=carta.id,
                    semanas_sequencia=sequencia_atual,
                    meta_sequencia=META_SEQUENCIA,
                    cupom=cupom_existente,
                    proxima_carta_em=proxima_data.strftime(
                        "%Y-%m-%dT%H:%M:%SZ"
                    ),
                )

        if carta.situacao != SituacaoCarta.disponivel:
            raise ErroDeNegocio(
                code="CARTA_NAO_DISPONIVEL",
                message=(
                    "Esta carta não está disponível para abertura."
                ),
                status=409,
            )

        especial = carta.tipo == TipoCarta.especial
        novo_cupom = (
            self._cupom_especial(carta, agora)
            if especial
            else self._cupom_da_semana(carta, agora)
        )

        self._cupons.salvar(novo_cupom)

        # Atualiza a carta aberta.
        carta.situacao = SituacaoCarta.aberta
        carta.aberta_em = agora.strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        carta.cupom_id = novo_cupom.id

        self._repository.atualizar(carta)

        # Incrementa a sequência de ofensiva. A carta especial fecha
        # o ciclo de 5 semanas: a sequencia volta a zero.
        nova_sequencia = (
            0
            if especial
            else self._sequencia(carta.cliente_id) + 1
        )

        self._repository.salvar_sequencia(
            carta.cliente_id,
            nova_sequencia,
        )

        # Agenda a próxima carta para sete dias depois.
        proxima_data = agora + timedelta(
            days=INTERVALO_CARTAS_DIAS
        )

        tipo_proxima_carta = (
            TipoCarta.especial
            if nova_sequencia == META_SEQUENCIA
            else TipoCarta.normal
        )

        proxima_carta = Carta(
            id=str(uuid.uuid4()),
            cliente_id=carta.cliente_id,
            semana=carta.semana + 1,
            tipo=tipo_proxima_carta,
            situacao=SituacaoCarta.bloqueada,
            disponivel_em=proxima_data.strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
        )

        self._repository.salvar(proxima_carta)

        return AberturaCartaResponse(
            carta_id=carta.id,
            semanas_sequencia=nova_sequencia,
            meta_sequencia=META_SEQUENCIA,
            cupom=novo_cupom,
            proxima_carta_em=proxima_data.strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
        )


    def _cupom_especial(self, carta: Carta, agora) -> Cupom:
        """Carta especial: sempre R$ 50 de desconto na proxima fatura."""

        valido_ate = agora + timedelta(days=VALIDADE_CUPOM_DIAS)

        return Cupom(
            id=str(uuid.uuid4()),
            cliente_id=carta.cliente_id,
            carta_id=carta.id,
            tag="BÔNUS DO CLUBE",
            titulo=f"R$ {BONUS_ESPECIAL_VALOR} de desconto na fatura",
            descricao=(
                "Prêmio por 5 semanas seguidas no Clube Bulbe: "
                "o desconto entra na sua próxima fatura."
            ),
            codigo=f"BULBE{BONUS_ESPECIAL_VALOR}-{uuid.uuid4().hex[:6].upper()}",
            parceiro=PARCEIRO_BULBE,
            situacao=SituacaoCupom.ativo,
            valido_ate=valido_ate.strftime("%Y-%m-%d"),
            dias_restantes=VALIDADE_CUPOM_DIAS,
            criado_em=relogio.instante_iso(agora),
        )

    def _cupom_da_semana(self, carta: Carta, agora) -> Cupom:
        """Carta normal: cupom de parceiro."""

        valido_ate = agora + timedelta(days=VALIDADE_CUPOM_DIAS)

        return Cupom(
            id=str(uuid.uuid4()),
            cliente_id=carta.cliente_id,
            carta_id=carta.id,
            tag="PARCERIA LIVELO",
            titulo="500 pontos Livelo",
            descricao=(
                "Use o cupom no app ou site da Livelo "
                "para liberar 500 pontos."
            ),
            codigo=(
                f"BULBELIV{agora.strftime('%d%m')}"
                f"{uuid.uuid4().hex[:6].upper()}"
            ),
            parceiro=ParceiroResumoCupom(
                id=PARCEIRO_PADRAO_ID,
                nome=PARCEIRO_PADRAO_NOME,
                categoria=PARCEIRO_PADRAO_CATEGORIA,
            ),
            situacao=SituacaoCupom.ativo,
            valido_ate=valido_ate.strftime("%Y-%m-%d"),
            dias_restantes=VALIDADE_CUPOM_DIAS,
            criado_em=relogio.instante_iso(agora),
        )


carta_service = CartaService(carta_repository)
