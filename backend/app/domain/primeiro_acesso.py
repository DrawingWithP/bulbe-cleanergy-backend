"""
Camada de Domínio, entidades e esquemas de Primeiro Acesso
(US-09 e US-10).
"""

from datetime import datetime
from enum import Enum

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class CanalVerificacao(str, Enum):
    whatsapp = "whatsapp"
    sms = "sms"
    email = "email"


class SituacaoVerificacao(str, Enum):
    pendente = "pendente"
    usada = "usada"
    expirada = "expirada"


class VerificacaoRequest(BaseModel):
    """
    Corpo da requisição para iniciar
    a verificação de primeiro acesso.

    POST /v1/primeiro-acesso/verificacoes
    US-09.
    """

    cpf: str = Field(
        ...,
        min_length=11,
        max_length=14,
        description=(
            "CPF do cliente cadastrado "
            "(com ou sem formatação)"
        ),
    )

    canal: CanalVerificacao = Field(
        default=CanalVerificacao.whatsapp,
        description=(
            "Canal escolhido para envio do código: "
            "whatsapp, sms ou email"
        ),
    )


class VerificacaoResponse(BaseModel):
    """
    Resposta ao solicitar o envio do código
    de confirmação (202 Accepted).
    """

    verificacao_id: str = Field(
        ...,
        description=(
            "Identificador único da solicitação "
            "de verificação"
        ),
    )

    canal: str = Field(
        ...,
        description="Canal utilizado para envio",
    )

    destino_mascarado: str = Field(
        ...,
        description=(
            "Telefone ou e-mail mascarado para "
            "onde o código foi enviado"
        ),
    )

    expira_em: str = Field(
        ...,
        description=(
            "Data/hora de expiração do código "
            "no padrão ISO 8601"
        ),
    )


class ConfirmacaoRequest(BaseModel):
    """
    Corpo da requisição para validar
    o código de confirmação.

    POST /v1/primeiro-acesso/confirmacoes
    US-10.
    """

    verificacao_id: str = Field(
        ...,
        description=(
            "Identificador único retornado "
            "na etapa de verificação"
        ),
    )

    codigo: str = Field(
        ...,
        min_length=6,
        max_length=6,
        pattern=r"^\d{6}$",
        description=(
            "Código numérico de 6 dígitos "
            "recebido pelo cliente"
        ),
    )


class ConfirmacaoResponse(BaseModel):
    """
    Resposta após a confirmação válida
    do código (201 Created).
    """

    cliente_id: str = Field(
        ...,
        description=(
            "Identificador do cliente no sistema"
        ),
    )

    acesso_habilitado: bool = Field(
        default=True,
        description=(
            "Indica se o acesso ao aplicativo "
            "foi habilitado com sucesso"
        ),
    )

    confirmado_em: str = Field(
        ...,
        description=(
            "Data/hora da confirmação "
            "no padrão ISO 8601"
        ),
    )


class Verificacao(BaseModel):
    """
    Representação interna da verificação
    de primeiro acesso.
    """

    model_config = ConfigDict(
        from_attributes=True
    )

    id: str
    cliente_id: str

    cpf: str = Field(
        ...,
        min_length=11,
        max_length=11,
    )

    canal: str

    codigo: str = Field(
        ...,
        min_length=6,
        max_length=6,
        pattern=r"^\d{6}$",
    )

    destino_mascarado: str
    expira_em: datetime

    tentativas: int = Field(
        default=0,
        ge=0,
    )

    situacao: SituacaoVerificacao = (
        SituacaoVerificacao.pendente
    )

    criado_em: datetime
