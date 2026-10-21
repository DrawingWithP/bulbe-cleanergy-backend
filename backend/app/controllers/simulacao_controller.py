"""
Camada de Apresentacao, SimulacaoController (APIRouter).
"""
from fastapi import APIRouter, status

from app.domain.simulacao import Simulacao, SimulacaoCreate
from app.services.simulacao_service import simulacao_service

router = APIRouter(prefix="/v1/simulacaos", tags=["Simulacaos"])

@router.post("", response_model=Simulacao, status_code=status.HTTP_201_CREATED)
def criar_simulacao(dados: SimulacaoCreate) -> Simulacao:
    """Cria uma nova simulacao."""
    return simulacao_service.criar(dados)