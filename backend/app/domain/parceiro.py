"""
Camada de Domínio, entidade Parceiro e esquemas Pydantic (US-02, US-24, US-25, US-26 e US-33).
"""
from pydantic import BaseModel, Field


class ParceiroBase(BaseModel):
    nome: str = Field(..., min_length=2, max_length=100, description="Nome da empresa parceira")
    categoria: str = Field(..., min_length=2, max_length=60, description="Categoria de atuação")
    logo_url: str | None = Field(None, max_length=255, description="URL do logotipo da marca parceira")
    ativo: bool = Field(True, description="Indica se o parceiro está ativo no Clube")


class ParceiroCreate(ParceiroBase):
    """Campos exigidos ao cadastrar um novo parceiro (POST /v1/parceiros - US-24)."""
    pass


class ParceiroUpdate(BaseModel):
    """Campos atualizáveis do parceiro (PUT /v1/parceiros/{id})."""
    nome: str | None = Field(None, min_length=2, max_length=100)
    categoria: str | None = Field(None, min_length=2, max_length=60)
    logo_url: str | None = Field(None, max_length=255)
    ativo: bool | None = None


class ParceiroCriadoResponse(BaseModel):
    id: str
    nome: str
    categoria: str
    ativo: bool
    criado_em: str


class Parceiro(ParceiroBase):
    """Representação completa de um parceiro do Clube Bulbe."""
    id: str
    criado_em: str
    atualizado_em: str | None = None

    class Config:
        from_attributes = True


class ParceiroListaPaginada(BaseModel):
    data: list[Parceiro]
    page: int
    total: int
