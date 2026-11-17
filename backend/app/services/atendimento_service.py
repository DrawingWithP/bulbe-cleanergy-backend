"""
Camada de Servico, atendimento pelo app (chat com robo e atendente).
"""

import logging
import uuid

from app.core import relogio
from app.domain.atendimento import (
    AbrirAtendimento,
    Atendimento,
    AtendimentoDetalhe,
    AtendimentoResumo,
    AutorMensagem,
    Mensagem,
    StatusAtendimento,
)
from app.repositories.atendimento_repository import (
    AtendimentoRepository,
    atendimento_repository,
)
from app.repositories.cliente_repository import (
    ClienteRepository,
    cliente_repository,
)
from app.services import atendimento_bot as bot


logger = logging.getLogger(__name__)

ASSUNTO_PADRAO = "Conversa pelo app"
ABERTOS = (
    StatusAtendimento.bot,
    StatusAtendimento.aguardando_atendente,
    StatusAtendimento.em_atendimento,
)


class ErroDeNegocio(Exception):
    """
    Erro de negocio com formato padronizado:
    code, message e status.
    """

    def __init__(self, code: str, message: str, status: int) -> None:
        self.code = code
        self.message = message
        self.status = status
        super().__init__(message)


class AtendimentoService:
    def __init__(
        self,
        repository: AtendimentoRepository,
        clientes: ClienteRepository = cliente_repository,
    ) -> None:
        self._repository = repository
        self._clientes = clientes

    # ------------------------------------------------------------ apoio
    def _cliente(self, cliente_id: str):
        cliente = self._clientes.buscar_por_id(cliente_id)
        if not cliente:
            raise ErroDeNegocio(
                code="RECURSO_NAO_ENCONTRADO",
                message=f"Cliente com id '{cliente_id}' nao foi encontrado.",
                status=404,
            )
        return cliente

    def _buscar(self, atendimento_id: str) -> Atendimento:
        atendimento = self._repository.buscar_por_id(atendimento_id)
        if atendimento is None:
            raise ErroDeNegocio(
                code="RECURSO_NAO_ENCONTRADO",
                message=f"Atendimento com id '{atendimento_id}' nao foi encontrado.",
                status=404,
            )
        return atendimento

    def _exigir_aberto(self, atendimento: Atendimento) -> None:
        if atendimento.status == StatusAtendimento.resolvido:
            raise ErroDeNegocio(
                code="ATENDIMENTO_ENCERRADO",
                message="Esta conversa ja foi encerrada. Abra uma nova conversa.",
                status=409,
            )

    def _mensagem(self, atendimento: Atendimento, autor: AutorMensagem, texto: str,
                  opcoes: list[str] | None = None) -> Mensagem:
        agora = relogio.instante_iso()
        mensagem = self._repository.adicionar_mensagem(atendimento.id, autor.value, texto, agora, opcoes)
        atendimento.atualizado_em = agora
        self._repository.salvar(atendimento)
        return mensagem

    def _dados_do_cliente(self, cliente_id: str) -> dict:
        """O que o robo usa para responder; uma falha aqui nao derruba a conversa."""
        dados: dict = {}
        try:
            from app.services.ativacao_service import ativacao_service
            dados["ativacao"] = ativacao_service.obter_resumo(cliente_id).model_dump()
        except Exception:  # noqa: BLE001
            logger.debug("Sem dados de ativacao para o robo", exc_info=True)
        try:
            from app.services.carta_service import carta_service
            dados["clube"] = carta_service.obter_situacao_clube(cliente_id).model_dump()
        except Exception:  # noqa: BLE001
            logger.debug("Sem dados do Clube para o robo", exc_info=True)
        try:
            from app.services.indicacao_service import indicacao_service
            dados["indicacoes"] = [i.model_dump(mode="json") for i in indicacao_service.listar_por_cliente(cliente_id)]
        except Exception:  # noqa: BLE001
            logger.debug("Sem indicacoes para o robo", exc_info=True)
        return dados

    # ------------------------------------------------------------ cliente
    def abrir(self, dados: AbrirAtendimento) -> AtendimentoDetalhe:
        cliente = self._cliente(dados.cliente_id)
        agora = relogio.instante_iso()
        atendimento = Atendimento(
            id=str(uuid.uuid4()),
            cliente_id=dados.cliente_id,
            assunto=(dados.assunto or "").strip() or ASSUNTO_PADRAO,
            status=StatusAtendimento.bot,
            criado_em=agora,
            atualizado_em=agora,
        )
        self._repository.salvar(atendimento)
        primeiro_nome = (cliente.nome or "").split()[0] if cliente.nome else "tudo bem"
        resposta = bot.boas_vindas(primeiro_nome)
        self._mensagem(atendimento, AutorMensagem.bot, resposta.texto, resposta.opcoes)
        return self.detalhar(atendimento.id)

    def listar_do_cliente(self, cliente_id: str) -> list[AtendimentoResumo]:
        self._cliente(cliente_id)
        return self._repository.listar(cliente_id=cliente_id)

    def detalhar(self, atendimento_id: str, depois_de: int = 0) -> AtendimentoDetalhe:
        atendimento = self._buscar(atendimento_id)
        return AtendimentoDetalhe(
            **atendimento.model_dump(),
            mensagens=self._repository.mensagens(atendimento_id, max(depois_de, 0)),
        )

    def enviar_do_cliente(self, atendimento_id: str, texto: str) -> list[Mensagem]:
        """
        Mensagem do cliente. Enquanto o robo atende, ele responde na hora;
        depois que o cliente pediu um atendente, a mensagem so entra na conversa.
        Devolve as mensagens novas (a do cliente e as respostas).
        """
        atendimento = self._buscar(atendimento_id)
        self._exigir_aberto(atendimento)
        novas = [self._mensagem(atendimento, AutorMensagem.cliente, texto.strip())]

        if atendimento.status != StatusAtendimento.bot:
            return novas

        resposta = bot.responder(texto, self._dados_do_cliente(atendimento.cliente_id))
        novas.append(self._mensagem(atendimento, AutorMensagem.bot, resposta.texto, resposta.opcoes))

        if resposta.acao == "atendente":
            atendimento.status = StatusAtendimento.aguardando_atendente
            novas.append(self._mensagem(atendimento, AutorMensagem.sistema,
                                        "Você entrou na fila de atendimento."))
        elif resposta.acao == "resolvido":
            self._encerrar(atendimento, None)
        return novas

    def encerrar(self, atendimento_id: str, avaliacao: int | None = None) -> AtendimentoDetalhe:
        atendimento = self._buscar(atendimento_id)
        if atendimento.status != StatusAtendimento.resolvido:
            self._encerrar(atendimento, avaliacao)
        elif avaliacao is not None:
            atendimento.avaliacao = avaliacao
            self._repository.salvar(atendimento)
        return self.detalhar(atendimento_id)

    def _encerrar(self, atendimento: Atendimento, avaliacao: int | None) -> None:
        agora = relogio.instante_iso()
        atendimento.status = StatusAtendimento.resolvido
        atendimento.encerrado_em = agora
        atendimento.avaliacao = avaliacao
        self._mensagem(atendimento, AutorMensagem.sistema, "Conversa encerrada.")

    # ------------------------------------------------------------ operador
    def fila(self, status: list[StatusAtendimento] | None = None) -> list[AtendimentoResumo]:
        valores = [s.value for s in (status or [])] or None
        return self._repository.listar(status=valores)

    def responder_como_atendente(self, atendimento_id: str, texto: str, atendente: str) -> Mensagem:
        atendimento = self._buscar(atendimento_id)
        self._exigir_aberto(atendimento)
        if atendimento.status != StatusAtendimento.em_atendimento or atendimento.atendente_nome != atendente:
            atendimento.status = StatusAtendimento.em_atendimento
            atendimento.atendente_nome = atendente
            self._mensagem(atendimento, AutorMensagem.sistema, f"{atendente} entrou na conversa.")
        return self._mensagem(atendimento, AutorMensagem.atendente, texto.strip())


atendimento_service = AtendimentoService(atendimento_repository)
