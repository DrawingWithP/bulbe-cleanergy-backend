"""
Camada de Dominio, catalogo de cupons do Clube Bulbe.

Cada item e um modelo de cupom de um parceiro. Quando o cliente abre a carta
normal da semana, a API sorteia um modelo ativo (com chance proporcional ao
peso) e gera um cupom com codigo unico para ele.
"""

from pydantic import BaseModel, ConfigDict, Field


PADRAO_PREFIXO = r"^[A-Z0-9]{3,12}$"


class CupomCatalogoBase(BaseModel):
    parceiro_id: str = Field(..., min_length=1, max_length=36)
    titulo: str = Field(..., min_length=3, max_length=120)
    descricao: str = Field(..., min_length=5, max_length=300)
    tag: str = Field(
        default="PARCERIA BULBE",
        min_length=3,
        max_length=60,
        description="Etiqueta exibida no cupom",
    )
    prefixo_codigo: str = Field(
        ...,
        pattern=PADRAO_PREFIXO,
        description="Inicio do codigo (letras maiusculas e numeros); o resto e gerado",
    )
    validade_dias: int = Field(default=14, ge=1, le=90)
    peso: int = Field(
        default=1,
        ge=1,
        le=10,
        description="Chance relativa no sorteio (1 a 10)",
    )
    ativo: bool = True


class CupomCatalogoCreate(CupomCatalogoBase):
    """Corpo do POST /v1/catalogo-cupons."""


class CupomCatalogoUpdate(BaseModel):
    """Corpo do PATCH /v1/catalogo-cupons/{id}: todos os campos opcionais."""

    parceiro_id: str | None = Field(default=None, min_length=1, max_length=36)
    titulo: str | None = Field(default=None, min_length=3, max_length=120)
    descricao: str | None = Field(default=None, min_length=5, max_length=300)
    tag: str | None = Field(default=None, min_length=3, max_length=60)
    prefixo_codigo: str | None = Field(default=None, pattern=PADRAO_PREFIXO)
    validade_dias: int | None = Field(default=None, ge=1, le=90)
    peso: int | None = Field(default=None, ge=1, le=10)
    ativo: bool | None = None


class CupomCatalogo(CupomCatalogoBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    parceiro_nome: str | None = None
    criado_em: str
    atualizado_em: str | None = None
