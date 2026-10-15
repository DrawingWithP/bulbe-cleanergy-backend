"""
Camada de Domínio, entidade Dica.
"""
from datetime import date
from enum import Enum
from pydantic import BaseModel, Field
class StatusDica(str, Enum):
    ativa = "ativa"
    em_manutencao = "em_manutencao"
    inativa = "inativa"
class DicaBase(BaseModel):
    titulo: str = Field(..., min_length=3, max_length=100, description="Titulo da dica")
    descricao: str = Field(..., min_length=3, max_length=250, description="Resumo do que fazer para a dica")
    economia: float = Field(..., gt=0, description="Economia mensal da dica")
    imagem_svg: str = Field(..., description="Código XML/Texto puro do arquivo SVG")
class DicaCreate(DicaBase):
    """Campos exigidos para criar uma dica (POST)."""
    pass
class DicaUpdate(BaseModel):
    """Campos que podem ser atualizados (PUT). Todos opcionais."""
    titulo: str | None = Field(None, min_length=3, max_length=100)
    descricao: str | None = Field(None, min_length=3, max_length=250)
    economia: float | None = Field(None, gt=0)
    imagem_svg: str | None = Field(None)
class Dica(DicaBase):
    """Representacao completa de uma dica, como a API devolve."""
    id: int
    data_ativacao: date
    class Config:
        from_attributes = True        