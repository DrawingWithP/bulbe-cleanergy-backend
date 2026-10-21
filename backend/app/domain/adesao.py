"""
Camada de domínio, entidade Adesão
"""

from datetime import date
from enum import Enum
from pydantic import BaseModel, Field

class StatusAdesao(str,enum):
    rascunho = "rascunho"
    enviada = "enviada"
    aprovada = "aprovada"
    recusada = "recusada"
class AdesaoBase(BaseModel):
    nome: str = Field(..., min_length=3, max_length=100, description="Nome do cliente")
    email: str = Field(..., min_length=3, max_length=100, description="Endereço de email do cliente")
    cpf: str = Field(..., min_length=11, max_length=11, description="CPF do cliente")
    telefone: str = Field(..., min_length=8, max_length=12, description="Telefone do cliente")
    cep: str = Field(..., min_length=8, max_length=8, description="CEP do cliente")
    logradouro: str = Field(..., min_length=4, max_length=100, description="Logradouro do endereço do cliente")
    numero: int = Field(..., gt=0, description="Número do endereço do cliente")
    bairro: str = Field(..., min_length=3, max_length=40, description="Bairro do cliente")
    cidade: str = Field(..., min_length=3, max_length=40, description="Cidade do cliente")
    uf: str = Field(..., min_length=2, max_length=2, description="Unidade federativa do cliente")
    distribuidora: str = Field(..., min_length=4, max_length=15, description="Distribuidora do cliente")
    numero_instalacao: str = Field(..., description="Número da instalação do cliente")
    valor_conta_atual: float = Field(..., gt=0, description="Valor da conta de luz atual do cliente")
    status: StatusAdesao = StatusAdesao.enviada
class AdesaoCreate(AdesaoBase):
    """Campos exigidos para criar uma adesão (POST)."""
    pass
class AdesaoUpdate(BaseModel):
    """Campos que podem ser atualizados (PUT). Todos opcionais."""
    nome: str | None = Field(..., min_length=3, max_length=100, description="Nome do cliente")
    email: str | None = Field(..., min_length=3, max_length=100, description="Endereço de email do cliente")
    cpf: str | None = Field(..., min_length=11, max_length=11, description="CPF do cliente")
    telefone: str | None = Field(..., min_length=8, max_length=12, description="Telefone do cliente")
    status: StatusAdesao | None = None
class Adesao(AdesaoBase):
    """Representacao completa de uma adesão, como a API devolve."""
    id: int
    data_ativacao: date
    class Config:
        from_attributes = True        