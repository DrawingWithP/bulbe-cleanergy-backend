"""
Camada de Domínio, entidades e esquemas de Primeiro Acesso (US-09 e US-10).
"""
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class CanalVerificacao(str, Enum):
    whatsapp = "whatsapp"
    sms = "sms"
    email = "email"


class SituacaoVerificacao(str, Enum):
    pendente = "pendente"
    usada = "usada"
    expirada = "expirada"


class VerificacaoRequest(BaseModel):
    """Corpo da requisição para iniciar verificação de primeiro acesso (POST /v1/primeiro-acesso/verificacoes)."""
    cpf: str = Field(..., description="CPF do cliente cadastrado (com ou sem formatação)")
    canal: CanalVerificacao = Field(
        default=CanalVerificacao.whatsapp,
        description="Canal escolhido para envio do código: whatsapp ou sms",
    )


class VerificacaoResponse(BaseModel):
    """Resposta ao solicitar envio do código de confirmação (202 Accepted)."""
    verificacao_id: str = Field(..., description="Identificador único da solicitação de verificação")
    canal: str = Field(..., description="Canal utilizado para envio")
    destino_mascarado: str = Field(..., description="Telefone ou e-mail mascarado para onde o código foi enviado")
    expira_em: str = Field(..., description="Data/hora de expiração do código no padrão ISO 8601")


class ConfirmacaoRequest(BaseModel):
    """Corpo da requisição para validar o código de confirmação (POST /v1/primeiro-acesso/confirmacoes)."""
    verificacao_id: str = Field(..., description="Identificador único retornado na etapa de verificação")
    codigo: str = Field(..., min_length=4, max_length=10, description="Código recebido pelo cliente")


class ConfirmacaoResponse(BaseModel):
    """Resposta após a confirmação válida do código (201 Created)."""
    cliente_id: str = Field(..., description="Identificador do cliente no sistema")
    acesso_habilitado: bool = Field(True, description="Indica se o acesso ao aplicativo foi habilitado com sucesso")
    confirmado_em: str = Field(..., description="Data/hora da confirmação no padrão ISO 8601")


class Verificacao(BaseModel):
    """Representação interna da verificação de primeiro acesso."""
    id: str
    cliente_id: str
    cpf: str
    canal: str
    codigo: str
    destino_mascarado: str
    expira_em: datetime
    tentativas: int = 0
    situacao: SituacaoVerificacao = SituacaoVerificacao.pendente
    criado_em: datetime

    class Config:
        from_attributes = True
