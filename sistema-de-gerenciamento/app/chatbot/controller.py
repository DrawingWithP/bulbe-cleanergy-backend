"""
Camada de Apresentacao, ChatbotController (APIRouter).

Rotas do chat do Painel de Gestao (secao 3.1 do contrato e secao 2.1 do contrato
das melhorias). Todas exigem funcionario logado. As rotas sao sincronas (def): o
FastAPI as executa em thread separada, entao a chamada bloqueante a API do Claude
nao trava o servidor. No stream, o gerador sincrono e consumido pelo Starlette
tambem em thread separada.
"""
import json
import logging
from typing import Iterator, Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator

from app.chatbot import config
from app.chatbot.servico import chatbot_service
from app.erros import ErroDeNegocio
from app.painel.auth import funcionario_logado

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/painel/chat", tags=["Chatbot"])

SUGESTOES: list[str] = [
    "Em que etapa da ativação está o Marcos Andrade?",
    "Quais clientes têm fatura vencida?",
    "Quais clientes estão parados há mais de 30 dias na mesma etapa da ativação?",
    "Como estão as ativações? Quantos clientes em cada etapa e quantos atrasados?",
    "Como funciona o Clube Bulbe?",
    "Quanto um cliente com conta de R$ 320 economiza em 12 meses indicando 2 amigos?",
    "Quantas adesões estão aguardando análise (situação enviada)?",
    "Quais atendimentos estão em aberto?",
    "Qual a diferença entre o que é responsabilidade da CEMIG e da Bulbe?",
    "Quais funcionalidades do app foram criadas pela squad Cleanergy?",
]

# Cabecalhos do stream: sem cache e sem buffer em proxies (ex.: nginx), para o texto chegar na hora.
CABECALHOS_SSE: dict[str, str] = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}


class MensagemHistorico(BaseModel):
    """Uma troca anterior da conversa (so texto) — formato da v1."""

    papel: Literal["funcionario", "assistente"]
    texto: str = Field(max_length=40000)


class PerguntaChat(BaseModel):
    """Corpo de POST /v1/painel/chat e /v1/painel/chat/stream."""

    mensagem: str = Field(min_length=1, max_length=2000)
    conversa_id: str | None = Field(default=None, max_length=64)
    historico: list[MensagemHistorico] = Field(default_factory=list, max_length=20)

    @field_validator("mensagem")
    @classmethod
    def mensagem_nao_vazia(cls, valor: str) -> str:
        if not valor.strip():
            raise ValueError("a mensagem nao pode ser vazia")
        return valor.strip()

    @field_validator("conversa_id")
    @classmethod
    def conversa_id_vazio_vira_none(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        return valor.strip() or None


class UsoChat(BaseModel):
    """Tokens somados de todas as voltas da pergunta e o custo estimado."""

    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    custo_estimado_usd: float = 0.0


class RespostaChat(BaseModel):
    """Resposta de POST /v1/painel/chat."""

    resposta: str
    ferramentas_usadas: list[str]
    modelo: str
    conversa_id: str | None = None
    uso: UsoChat = Field(default_factory=UsoChat)


class SugestoesChat(BaseModel):
    """Resposta de GET /v1/painel/chat/sugestoes."""

    sugestoes: list[str]


class ConversaResumo(BaseModel):
    """Item de GET /v1/painel/chat/conversas."""

    id: str
    titulo: str | None = None
    criado_em: str | None = None
    atualizado_em: str | None = None
    total_mensagens: int = 0


class ListaConversas(BaseModel):
    """Resposta de GET /v1/painel/chat/conversas."""

    conversas: list[ConversaResumo]


class MensagemVisivel(BaseModel):
    """Mensagem com texto visivel de uma conversa salva."""

    papel: Literal["funcionario", "assistente"]
    texto: str


class ConversaDetalhe(BaseModel):
    """Resposta de GET /v1/painel/chat/conversas/{id}."""

    id: str
    titulo: str | None = None
    mensagens: list[MensagemVisivel]


# ---------------------------------------------------------------------------
# Server-Sent Events
# ---------------------------------------------------------------------------
def formatar_evento_sse(evento: dict) -> str:
    """Uma linha `data: <json>` seguida de linha em branco."""
    return f"data: {json.dumps(evento, ensure_ascii=False, default=str)}\n\n"


def _evento_erro(code: str, message: str, status: int) -> dict:
    return {"tipo": "erro", "error": {"code": code, "message": message, "status": status}}


def gerar_eventos_sse(eventos: Iterator[dict]) -> Iterator[str]:
    """
    Converte os eventos do servico em SSE. Erros no meio do stream viram o evento
    {"tipo": "erro", "error": {...}} (que encerra o stream) em vez de derrubar a conexao.
    """
    try:
        for evento in eventos:
            evento = dict(evento)
            if evento.get("tipo") == "fim":
                evento.pop("duracao_ms", None)
            yield formatar_evento_sse(evento)
    except ErroDeNegocio as exc:
        yield formatar_evento_sse(_evento_erro(exc.code, exc.message, exc.status))
    except Exception:  # noqa: BLE001 - nunca quebrar a conexao com um erro sem formato
        logger.exception("Chatbot: erro inesperado durante o stream.")
        yield formatar_evento_sse(
            _evento_erro("CHATBOT_ERRO_INTERNO", "O assistente teve um erro inesperado. Tente novamente.", 500)
        )


# ---------------------------------------------------------------------------
# Rotas
# ---------------------------------------------------------------------------
@router.post("", response_model=RespostaChat)
def conversar(dados: PerguntaChat, funcionario: dict = Depends(funcionario_logado)) -> RespostaChat:
    """
    Envia uma pergunta ao assistente e devolve a resposta completa.
    Com `conversa_id`, o historico vem do servidor (e `historico` e ignorado);
    sem ele, cria uma conversa nova (aceitando o `historico` de texto da v1).
    """
    resultado = chatbot_service.responder(
        mensagem=dados.mensagem,
        historico=[item.model_dump() for item in dados.historico],
        funcionario=funcionario,
        conversa_id=dados.conversa_id,
    )
    return RespostaChat(**resultado)


@router.post("/stream")
def conversar_stream(dados: PerguntaChat, funcionario: dict = Depends(funcionario_logado)) -> StreamingResponse:
    """
    Mesma pergunta de POST /v1/painel/chat, com a resposta em Server-Sent Events:
    inicio -> texto/ferramenta (em ordem) -> fim, ou erro.
    Falhas detectadas antes de comecar (sem chave da API, conversa inexistente ou de outro
    funcionario, conversa longa demais) respondem com o status HTTP normal, sem stream.
    """
    contexto = chatbot_service.preparar(
        dados.mensagem,
        funcionario,
        conversa_id=dados.conversa_id,
        historico=[item.model_dump() for item in dados.historico],
    )
    eventos = chatbot_service.executar(contexto, ao_vivo=True)
    return StreamingResponse(gerar_eventos_sse(eventos), media_type="text/event-stream", headers=CABECALHOS_SSE)


@router.get("/conversas", response_model=ListaConversas)
def listar_conversas(
    limite: int = Query(default=config.LIMITE_CONVERSAS_LISTADAS, ge=1, le=100),
    funcionario: dict = Depends(funcionario_logado),
) -> ListaConversas:
    """Conversas do funcionario logado (mais recentes primeiro)."""
    return ListaConversas(conversas=chatbot_service.listar_conversas(funcionario, limite=limite))


@router.get("/conversas/{conversa_id}", response_model=ConversaDetalhe)
def obter_conversa(conversa_id: str, funcionario: dict = Depends(funcionario_logado)) -> ConversaDetalhe:
    """Mensagens com texto visivel de uma conversa do funcionario logado (404 se nao for dele)."""
    return ConversaDetalhe(**chatbot_service.obter_conversa_visivel(conversa_id, funcionario))


@router.get("/sugestoes", response_model=SugestoesChat)
def listar_sugestoes(funcionario: dict = Depends(funcionario_logado)) -> SugestoesChat:
    """Exemplos de perguntas para exibir na interface do chat."""
    return SugestoesChat(sugestoes=list(SUGESTOES))
