"""
Camada de Domínio, entidade Cliente e esquemas Pydantic
(US-05, US-31 e US-34).
"""

from enum import Enum

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
)


class StatusCliente(str, Enum):
    ativo = "ativo"
    em_ativacao = "em_ativacao"
    cancelado = "cancelado"


class Endereco(BaseModel):
    cep: str = Field(
        ...,
        min_length=8,
        max_length=10,
        description="CEP no formato 00000-000 ou somente dígitos",
    )

    logradouro: str = Field(
        ...,
        min_length=2,
        max_length=150,
    )

    numero: str = Field(
        ...,
        min_length=1,
        max_length=20,
    )

    complemento: str | None = Field(
        default=None,
        max_length=100,
    )

    bairro: str = Field(
        ...,
        min_length=2,
        max_length=100,
    )

    cidade: str = Field(
        ...,
        min_length=2,
        max_length=100,
    )

    uf: str = Field(
        ...,
        min_length=2,
        max_length=2,
    )


class EnderecoUpdate(BaseModel):
    cep: str | None = Field(
        default=None,
        min_length=8,
        max_length=10,
    )

    logradouro: str | None = Field(
        default=None,
        min_length=2,
        max_length=150,
    )

    numero: str | None = Field(
        default=None,
        min_length=1,
        max_length=20,
    )

    complemento: str | None = Field(
        default=None,
        max_length=100,
    )

    bairro: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
    )

    cidade: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
    )

    uf: str | None = Field(
        default=None,
        min_length=2,
        max_length=2,
    )


class ClienteCreate(BaseModel):
    """
    Dados exigidos ao criar um cliente.

    POST /v1/clientes
    US-31.
    """

    nome: str = Field(
        ...,
        min_length=3,
        max_length=120,
    )

    email: EmailStr

    cpf: str = Field(
        ...,
        min_length=11,
        max_length=14,
        description="CPF válido do cliente",
    )

    telefone: str = Field(
        ...,
        min_length=10,
        max_length=20,
    )

    endereco: Endereco

    distribuidora: str = Field(
        default="CEMIG",
        min_length=2,
        max_length=50,
    )

    numero_instalacao: str = Field(
        ...,
        min_length=3,
        max_length=30,
    )


class ClienteUpdate(BaseModel):
    """
    Dados cadastrais atualizáveis.

    PUT /v1/clientes/{id}
    US-34.
    """

    nome: str | None = Field(
        default=None,
        min_length=3,
        max_length=120,
    )

    telefone: str | None = Field(
        default=None,
        min_length=10,
        max_length=20,
    )

    endereco: EnderecoUpdate | None = None

    distribuidora: str | None = Field(
        default=None,
        min_length=2,
        max_length=50,
    )

    numero_instalacao: str | None = Field(
        default=None,
        min_length=3,
        max_length=30,
    )


class ClienteCriadoResponse(BaseModel):
    """
    Resposta após a criação do cliente
    (201 Created).
    """

    id: str
    nome: str
    email: str
    status: StatusCliente
    criado_em: str


class Cliente(BaseModel):
    """
    Representação completa do cliente.

    GET /v1/clientes/{id}
    US-05.
    """

    model_config = ConfigDict(
        from_attributes=True
    )

    id: str
    nome: str
    email: str
    cpf: str
    telefone: str
    endereco: Endereco
    distribuidora: str
    numero_instalacao: str
    status: StatusCliente
    acesso_habilitado: bool = False
    criado_em: str


class ClienteResumo(BaseModel):
    """
    Item resumido utilizado na listagem de clientes.
    """

    id: str
    nome: str
    email: str
    cpf: str
    telefone: str
    cidade: str
    uf: str
    status: StatusCliente
    criado_em: str


class ClienteListaPaginada(BaseModel):
    data: list[ClienteResumo]

    page: int = Field(
        ...,
        ge=1,
    )

    total: int = Field(
        ...,
        ge=0,
    )
