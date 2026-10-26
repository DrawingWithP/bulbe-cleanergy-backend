"""
Camada de Serviço, CartaService e Clube Bulbe (US-18, US-19, US-20 e US-21).
"""
from datetime import datetime, timedelta, timezone
import uuid

from app.domain.carta import (
    AberturaCartaResponse,
    Carta,
    CartaListaPaginada,
    ClubeSituacaoResponse,
    ProximaCartaInfo,
    SituacaoCarta,
    TipoCarta,
)
from app.domain.cupom import Cupom, ParceiroResumoCupom, SituacaoCupom
from app.repositories.carta_repository import CartaRepository, carta_repository
from app.repositories.cliente_repository import cliente_repository
from app.repositories.cupom_repository import cupom_repository
from app.repositories.parceiro_repository import parceiro_repository


class ErroDeNegocio(Exception):
    def __init__(self, code: str, message: str, status: int) -> None:
        self.code = code
        self.message = message
        self.status = status
        super().__init__(message)


class CartaService:
    def __init__(self, repository: CartaRepository) -> None:
        self._repository = repository
        self._sequencias: dict[str, int] = {"8f1c2a6e-4b7d-4c1a-9f52-3d6a1b0c7e11": 3}

    def obter_situacao_clube(self, cliente_id: str) -> ClubeSituacaoResponse:
        """US-18: Retorna a situação do cliente no Clube Bulbe (ofensiva e status da próxima carta)."""
        if not cliente_repository.buscar_por_id(cliente_id):
            raise ErroDeNegocio(
                code="RECURSO_NAO_ENCONTRADO",
                message=f"Cliente com id '{cliente_id}' não foi encontrado.",
                status=404,
            )

        carta_disp = self._repository.buscar_disponivel_cliente(cliente_id)
        sequencia = self._sequencias.get(cliente_id, 0)
        agora = datetime.now(timezone.utc)

        proxima_info = None
        if carta_disp:
            proxima_info = ProximaCartaInfo(
                carta_id=carta_disp.id,
                disponivel_em=carta_disp.disponivel_em,
                dias_restantes=0,
            )
        else:
            proxima_data = agora + timedelta(days=4)
            proxima_info = ProximaCartaInfo(
                carta_id="proxima-carta-agendada",
                disponivel_em=proxima_data.strftime("%Y-%m-%dT%H:%M:%SZ"),
                dias_restantes=4,
            )

        return ClubeSituacaoResponse(
            cliente_id=cliente_id,
            semanas_sequencia=sequencia,
            meta_sequencia=5,
            carta_disponivel=(carta_disp is not None),
            bonus_especial_pendente=(sequencia >= 5),
            proxima_carta=proxima_info,
            intervalo_dias=7,
        )

    def listar_cartas_cliente(
        self,
        cliente_id: str,
        page: int = 1,
        limit: int = 20,
        situacao: SituacaoCarta | None = None,
    ) -> CartaListaPaginada:
        """US-19: Lista o histórico de cartas semanais do cliente."""
        if not cliente_repository.buscar_por_id(cliente_id):
            raise ErroDeNegocio(
                code="RECURSO_NAO_ENCONTRADO",
                message=f"Cliente com id '{cliente_id}' não foi encontrado.",
                status=404,
            )

        cartas, total = self._repository.listar_por_cliente(cliente_id, page, limit, situacao)
        return CartaListaPaginada(data=cartas, page=page, total=total)

    def buscar_por_id(self, carta_id: str) -> Carta:
        """US-20: Consulta os dados de uma carta específica."""
        carta = self._repository.buscar_por_id(carta_id)
        if not carta:
            raise ErroDeNegocio(
                code="RECURSO_NAO_ENCONTRADO",
                message=f"Carta com id '{carta_id}' não foi encontrada.",
                status=404,
            )
        return carta

    def abrir_carta(self, carta_id: str) -> AberturaCartaResponse:
        """US-21: Abre a carta semanal, gera a recompensa em cupom e avança a ofensiva."""
        carta = self.buscar_por_id(carta_id)

        # Idempotência: se já aberta, recupera o mesmo cupom gerado
        if carta.situacao == SituacaoCarta.aberta and carta.cupom_id:
            cupom_existente = cupom_repository.buscar_por_id(carta.cupom_id)
            if cupom_existente:
                sequencia_atual = self._sequencias.get(carta.cliente_id, 3)
                proxima_em = (datetime.now(timezone.utc) + timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
                return AberturaCartaResponse(
                    carta_id=carta.id,
                    semanas_sequencia=sequencia_atual,
                    meta_sequencia=5,
                    cupom=cupom_existente,
                    proxima_carta_em=proxima_em,
                )

        if carta.situacao not in [SituacaoCarta.disponivel]:
            raise ErroDeNegocio(
                code="CARTA_NAO_DISPONIVEL",
                message="Esta carta não está disponível para abertura.",
                status=409,
            )

        agora = datetime.now(timezone.utc)
        valido_ate = (agora + timedelta(days=14)).strftime("%Y-%m-%d")
        novo_cupom_id = str(uuid.uuid4())

        # Seleciona parceiro ativo ou padrão Livelo
        parceiro_nome = "Livelo"
        parceiro_cat = "Programa de pontos"
        parceiro_id = "3e5a7c19-8b24-4d60-a1f3-7c9e2b5d8a06"

        novo_cupom = Cupom(
            id=novo_cupom_id,
            cliente_id=carta.cliente_id,
            carta_id=carta.id,
            tag="PARCERIA LIVELO",
            titulo="500 pontos Livelo",
            descricao="Use o cupom no app ou site da Livelo para liberar 500 pontos.",
            codigo=f"BULBELIV{agora.strftime('%d%m')}",
            parceiro=ParceiroResumoCupom(
                id=parceiro_id,
                nome=parceiro_nome,
                categoria=parceiro_cat,
            ),
            situacao=SituacaoCupom.ativo,
            valido_ate=valido_ate,
            dias_restantes=14,
            criado_em=agora.strftime("%Y-%m-%dT%H:%M:%SZ"),
        )
        cupom_repository.salvar(novo_cupom)

        # Atualiza a carta
        carta.situacao = SituacaoCarta.aberta
        carta.aberta_em = agora.strftime("%Y-%m-%dT%H:%M:%SZ")
        carta.cupom_id = novo_cupom.id
        self._repository.atualizar(carta)

        # Incrementa sequência de ofensiva
        nova_sequencia = self._sequencias.get(carta.cliente_id, 0) + 1
        self._sequencias[carta.cliente_id] = nova_sequencia

        # Agenda a próxima carta para 7 dias depois
        proxima_data = agora + timedelta(days=7)
        proxima_carta = Carta(
            id=str(uuid.uuid4()),
            cliente_id=carta.cliente_id,
            semana=carta.semana + 1,
            tipo=TipoCarta.especial if nova_sequencia == 5 else TipoCarta.normal,
            situacao=SituacaoCarta.bloqueada,
            disponivel_em=proxima_data.strftime("%Y-%m-%dT%H:%M:%SZ"),
        )
        self._repository.salvar(proxima_carta)

        return AberturaCartaResponse(
            carta_id=carta.id,
            semanas_sequencia=nova_sequencia,
            meta_sequencia=5,
            cupom=novo_cupom,
            proxima_carta_em=proxima_data.strftime("%Y-%m-%dT%H:%M:%SZ"),
        )


carta_service = CartaService(carta_repository)
