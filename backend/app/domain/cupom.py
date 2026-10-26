"""
Camada de Domínio, entidade Cupom e esquemas Pydantic (US-03, US-22 e US-23).
"""
from enum import Enum
from pydantic import BaseModel, Field


class SituacaoCupom(str, Enum):
    ativo = "ativo"
    salvo = "salvo"
    usado = "usado"
    expirado = "expirado"
    descartado = "descartado"


class ParceiroResumoCupom(BaseModel):
    id: str
    nome: str
    categoria: str


class CupomBase(BaseModel):
    cliente_id: str = Field(..., description="ID do cliente dono do cupom")
    carta_id: str | None = Field(None, description="ID da carta que gerou o cupom")
    tag: str = Field(default="PARCERIA BULBE", description="Tag de identificação da campanha")
    titulo: str = Field(..., min_length=3, max_length=120)
    descricao: str = Field(..., min_length=5, max_length=300)
    codigo: str = Field(..., min_length=3, max_length=30)
    parceiro: ParceiroResumoCupom
    situacao: SituacaoCupom = SituacaoCupom.ativo
    valido_ate: str = Field(..., description="Data limite de validade no padrão AAAA-MM-DD")


class CupomUpdate(BaseModel):
    """Atualização da situação do cupom (PATCH /v1/cupons/{id} - US-23)."""
    situacao: SituacaoCupom = Field(..., description="Nova situação: salvo ou usado")


class Cupom(CupomBase):
    """Representação completa do cupom (GET /v1/cupons/{id} - US-22)."""
    id: str
    dias_restantes: int = 14
    criado_em: str
    usado_em: str | None = None

    class Config:
        from_attributes = True


class CupomListaPaginada(BaseModel):
    """Listagem paginada de cupons do cliente (US-03)."""
    data: list[Cupom]
    page: int
    total: int
