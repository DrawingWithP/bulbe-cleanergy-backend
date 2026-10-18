"""
Camada de Apresentacao, ChatbotController (APIRouter).

Rotas do chat do Painel de Gestao (secao 3.1 do contrato). Todas exigem
funcionario logado. As rotas sao sincronas (def): o FastAPI as executa em
thread separada, entao a chamada bloqueante a API do Claude nao trava o servidor.
"""
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator

from app.chatbot.servico import chatbot_service
from app.painel.auth import funcionario_logado

router = APIRouter(prefix="/v1/painel/chat", tags=["Chatbot"])

SUGESTOES: list[str] = [
    "Em que etapa da ativação está o Marcos Andrade?",
    "Quais clientes têm fatura vencida?",
    "Como funciona o Clube Bulbe?",
    "Quanto um cliente com conta de R$ 320 economiza em 12 meses indicando 2 amigos?",
    "Quantas adesões estão aguardando análise (situação enviada)?",
    "Quais atendimentos estão em aberto?",
    "Qual a diferença entre o que é responsabilidade da CEMIG e da Bulbe?",
    "Quais funcionalidades do app foram criadas pela squad Cleanergy?",
]


class MensagemHistorico(BaseModel):
    """Uma troca anterior da conversa (so texto)."""

    papel: Literal["funcionario", "assistente"]
    texto: str = Field(max_length=40000)


class PerguntaChat(BaseModel):
    """Corpo de POST /v1/painel/chat."""

    mensagem: str = Field(min_length=1, max_length=2000)
    historico: list[MensagemHistorico] = Field(default_factory=list, max_length=20)

    @field_validator("mensagem")
    @classmethod
    def mensagem_nao_vazia(cls, valor: str) -> str:
        if not valor.strip():
            raise ValueError("a mensagem nao pode ser vazia")
        return valor.strip()


class RespostaChat(BaseModel):
    """Resposta de POST /v1/painel/chat."""

    resposta: str
    ferramentas_usadas: list[str]
    modelo: str


class SugestoesChat(BaseModel):
    """Resposta de GET /v1/painel/chat/sugestoes."""

    sugestoes: list[str]


@router.post("", response_model=RespostaChat)
def conversar(dados: PerguntaChat, funcionario: dict = Depends(funcionario_logado)) -> RespostaChat:
    """Envia uma pergunta ao assistente (com o historico da conversa) e devolve a resposta."""
    resultado = chatbot_service.responder(
        mensagem=dados.mensagem,
        historico=[item.model_dump() for item in dados.historico],
        funcionario=funcionario,
    )
    return RespostaChat(**resultado)


@router.get("/sugestoes", response_model=SugestoesChat)
def listar_sugestoes(funcionario: dict = Depends(funcionario_logado)) -> SugestoesChat:
    """Exemplos de perguntas para exibir na interface do chat."""
    return SugestoesChat(sugestoes=list(SUGESTOES))
