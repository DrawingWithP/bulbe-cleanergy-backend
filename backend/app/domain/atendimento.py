"""
Camada de Dominio, atendimento pelo app (chat com robo e atendente).

Fluxo: o cliente abre uma conversa no app (Fale conosco) e o robo responde
as duvidas mais comuns com os dados do proprio cliente. Se nao resolver, o
cliente pede um atendente: a conversa vai para a fila do sistema de
gerenciamento, onde um funcionario responde.
"""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class StatusAtendimento(str, Enum):
    bot = "bot"
    aguardando_atendente = "aguardando_atendente"
    em_atendimento = "em_atendimento"
    resolvido = "resolvido"


class AutorMensagem(str, Enum):
    cliente = "cliente"
    bot = "bot"
    atendente = "atendente"
    sistema = "sistema"


class Mensagem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    autor: AutorMensagem
    texto: str
    opcoes: list[str] | None = None
    criado_em: str


class Atendimento(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    cliente_id: str
    assunto: str
    status: StatusAtendimento
    atendente_nome: str | None = None
    avaliacao: int | None = None
    criado_em: str
    atualizado_em: str
    encerrado_em: str | None = None


class AtendimentoResumo(Atendimento):
    """Item da lista/fila, com a ultima mensagem."""

    cliente_nome: str | None = None
    ultima_mensagem: str | None = None
    total_mensagens: int = 0


class AtendimentoDetalhe(Atendimento):
    """Conversa com as mensagens (a partir de `depois_de`, para o polling)."""

    mensagens: list[Mensagem] = Field(default_factory=list)


class AbrirAtendimento(BaseModel):
    cliente_id: str = Field(..., min_length=1, max_length=36)
    assunto: str | None = Field(default=None, max_length=120)


class NovaMensagem(BaseModel):
    texto: str = Field(..., min_length=1, max_length=1000)


class RespostaAtendente(BaseModel):
    texto: str = Field(..., min_length=1, max_length=1000)
    atendente: str = Field(..., min_length=2, max_length=100, description="Nome exibido para o cliente")


class Encerramento(BaseModel):
    avaliacao: int | None = Field(default=None, ge=1, le=5, description="Nota de 1 a 5 (opcional)")
