"""
Testes unitarios da camada de Dominio: validacoes do Pydantic.
"""

import pytest
from pydantic import ValidationError

from app.domain.adesao import StatusAdesao, AdesaoCreate