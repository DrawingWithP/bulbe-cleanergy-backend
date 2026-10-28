"""
Testes unitarios da camada de Dominio: validacoes do Pydantic.
"""

import pytest
from pydantic import ValidationError

from app.domain.adesao import StatusAdesao, AdesaoCreate, AdesaoUpdate


@pytest.fixture
def dados_validos() -> dict:
    return {
        "nome": "João da Silva",
        "email": "joaosilva@gmail.com",
        "cpf": "14444444444",
        "telefone": "999999999",
        "cep": "34331312",
        "logradouro": "Rua Oliveira",
        "numero": 213,
        "bairro": "Buritis",
        "cidade": "Belo Horizonte",
        "uf": "MG",
        "distribuidora": "Cemig",
        "numero_instalacao": "3242412",
        "valor_conta_atual": 399.00,
    }


def test_adesao_valida_tem_status_enviada_por_padrao(dados_validos: dict):
    adesao = AdesaoCreate(**dados_validos)
    assert adesao.status == StatusAdesao.enviada


@pytest.mark.parametrize(
    "campo, valor",
    [
        ("cpf", "1234567890"),        # 10 dígitos
        ("cpf", "123456789012"),      # 12 dígitos
        ("cep", "3433131"),           # 7 dígitos
        ("uf", "MGS"),                # UF com 3 letras
        ("nome", "Jo"),               # nome curto
        ("telefone", "9999999"),      # telefone com 7 dígitos
        ("numero", 0),                # número precisa ser > 0
        ("valor_conta_atual", 0),     # valor precisa ser > 0
        ("valor_conta_atual", -10.5),
        ("distribuidora", "Cem"),     # distribuidora < 4 caracteres
        ("status", "cancelada"),      # status fora do enum
    ],
)
def test_adesao_com_campo_invalido_e_rejeitada(dados_validos: dict, campo: str, valor):
    with pytest.raises(ValidationError):
        AdesaoCreate(**{**dados_validos, campo: valor})


@pytest.mark.parametrize("campo", ["nome", "cpf", "numero_instalacao", "valor_conta_atual"])
def test_adesao_sem_campo_obrigatorio_e_rejeitada(dados_validos: dict, campo: str):
    dados_validos.pop(campo)
    with pytest.raises(ValidationError):
        AdesaoCreate(**dados_validos)


@pytest.mark.xfail(
    strict=True,
    reason=(
        "BUG: AdesaoUpdate usa Field(...) nos campos opcionais, o que os torna "
        "obrigatorios; nao da para atualizar so o status ou so o telefone."
    ),
)
def test_adesao_update_aceita_atualizacao_parcial():
    """O docstring do AdesaoUpdate diz 'Todos opcionais'."""
    atualizacao = AdesaoUpdate(status=StatusAdesao.aprovada)
    assert atualizacao.status == StatusAdesao.aprovada
