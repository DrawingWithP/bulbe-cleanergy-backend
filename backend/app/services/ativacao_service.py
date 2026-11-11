"""
Camada de Serviço, AtivacaoService (regras de negócio para US-11 e US-12).
"""

from datetime import datetime, timedelta, timezone

from app.domain.ativacao import (
    AtivacaoAtualizadaResponse,
    AtivacaoCliente,
    AtivacaoResumoResponse,
    AtivacaoUpdateRequest,
    EtapaDetalhe,
    EtapasListaResponse,
    SituacaoEtapa,
)
from app.repositories.ativacao_repository import (
    AtivacaoRepository,
    ativacao_repository,
)
from app.repositories.cliente_repository import (
    ClienteRepository,
    cliente_repository,
)


class ErroDeNegocio(Exception):
    def __init__(self, code: str, message: str, status: int) -> None:
        self.code = code
        self.message = message
        self.status = status
        super().__init__(message)


ETAPAS_CONFIG = [
    {
        "numero": 1,
        "nome": "Cadastro",
        "titulo": "Cadastro realizado",
        "descricao": "Seu cadastro foi concluído com sucesso.",
        "percentual": 15,
    },
    {
        "numero": 2,
        "nome": "Documentos",
        "titulo": "Documentação sendo analisada",
        "descricao": (
            "Seus documentos estão em análise. "
            "Em breve entraremos em contato."
        ),
        "percentual": 30,
    },
    {
        "numero": 3,
        "nome": "Solicitação",
        "titulo": "Solicitação enviada à CEMIG",
        "descricao": (
            "A Bulbe protocolou o pedido para a CEMIG "
            "liberar sua conexão."
        ),
        "percentual": 45,
    },
    {
        "numero": 4,
        "nome": "Análise CEMIG",
        "titulo": "Em análise pela CEMIG",
        "descricao": "Aguardando aprovação da CEMIG.",
        "percentual": 75,
    },
    {
        "numero": 5,
        "nome": "Energia liberada",
        "titulo": "Energia aprovada",
        "descricao": (
            "Em breve ela será liberada e seu desconto "
            "vai começar a aparecer na fatura."
        ),
        "percentual": 100,
    },
]


class AtivacaoService:
    def __init__(
        self,
        repository: AtivacaoRepository,
        clientes: ClienteRepository = cliente_repository,
    ) -> None:
        self._repository = repository
        self._clientes = clientes

    def _obter_registro(self, cliente_id: str) -> AtivacaoCliente:
        cliente = self._clientes.buscar_por_id(cliente_id)

        if not cliente:
            raise ErroDeNegocio(
                code="RECURSO_NAO_ENCONTRADO",
                message=f"Cliente com id '{cliente_id}' não foi encontrado.",
                status=404,
            )

        ativacao = self._repository.buscar_por_cliente_id(cliente_id)

        if not ativacao:
            # Inicializa jornada padrão para o cliente.
            agora = datetime.now(timezone.utc)
            prazo_ativacao_dias = 90
            previsao = agora + timedelta(days=prazo_ativacao_dias)

            ativacao = AtivacaoCliente(
                cliente_id=cliente_id,
                etapa_atual=1,
                distribuidora=cliente.distribuidora or "CEMIG",
                prazo_ativacao_dias=prazo_ativacao_dias,
                previsao_conclusao=previsao.strftime("%Y-%m-%d"),
                atualizado_em=agora.strftime("%Y-%m-%dT%H:%M:%SZ"),
            )

            self._repository.salvar_ou_atualizar(ativacao)

        return ativacao

    def obter_resumo(
        self,
        cliente_id: str,
    ) -> AtivacaoResumoResponse:
        """US-11: Retorna resumo do status e progresso de ativação."""

        ativacao = self._obter_registro(cliente_id)
        config_etapa = ETAPAS_CONFIG[ativacao.etapa_atual - 1]

        return AtivacaoResumoResponse(
            cliente_id=ativacao.cliente_id,
            etapa_atual=ativacao.etapa_atual,
            total_etapas=len(ETAPAS_CONFIG),
            percentual_concluido=config_etapa["percentual"],
            titulo=config_etapa["titulo"],
            descricao=config_etapa["descricao"],
            distribuidora=ativacao.distribuidora,
            prazo_ativacao_dias=ativacao.prazo_ativacao_dias,
            previsao_conclusao=ativacao.previsao_conclusao,
            atualizado_em=ativacao.atualizado_em,
        )

    def listar_etapas(
        self,
        cliente_id: str,
    ) -> EtapasListaResponse:
        """Lista as etapas da jornada e sua situação atual para o cliente."""

        ativacao = self._obter_registro(cliente_id)
        etapa_atual = ativacao.etapa_atual

        etapas: list[EtapaDetalhe] = []

        for conf in ETAPAS_CONFIG:
            numero = conf["numero"]

            if numero < etapa_atual:
                situacao = SituacaoEtapa.concluida
                concluida_em = ativacao.atualizado_em[:10]

            elif numero == etapa_atual:
                situacao = SituacaoEtapa.atual
                concluida_em = None

            else:
                situacao = SituacaoEtapa.pendente
                concluida_em = None

            etapas.append(
                EtapaDetalhe(
                    numero=numero,
                    nome=conf["nome"],
                    titulo=conf["titulo"],
                    descricao=conf["descricao"],
                    situacao=situacao,
                    concluida_em=concluida_em,
                )
            )

        return EtapasListaResponse(
            data=etapas,
            total=len(ETAPAS_CONFIG),
        )

    def atualizar_etapa(
        self,
        cliente_id: str,
        dados: AtivacaoUpdateRequest,
    ) -> AtivacaoAtualizadaResponse:
        """US-12: Atualiza a etapa atual da jornada."""

        total_etapas = len(ETAPAS_CONFIG)

        if dados.etapa_atual < 1 or dados.etapa_atual > total_etapas:
            raise ErroDeNegocio(
                code="ETAPA_INVALIDA",
                message=f"A etapa atual deve estar entre 1 e {total_etapas}.",
                status=400,
            )

        ativacao = self._obter_registro(cliente_id)

        ativacao.etapa_atual = dados.etapa_atual
        ativacao.atualizado_em = datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )

        if dados.observacao:
            ativacao.observacoes.append(dados.observacao)

        self._repository.salvar_ou_atualizar(ativacao)

        config_etapa = ETAPAS_CONFIG[ativacao.etapa_atual - 1]

        return AtivacaoAtualizadaResponse(
            cliente_id=ativacao.cliente_id,
            etapa_atual=ativacao.etapa_atual,
            percentual_concluido=config_etapa["percentual"],
            titulo=config_etapa["titulo"],
            atualizado_em=ativacao.atualizado_em,
        )


ativacao_service = AtivacaoService(ativacao_repository)
