"""
Testes unitários das funções de segurança (hash de senha e tokens JWT).
"""
from datetime import timedelta

import jwt
import pytest

from app.core.config import ALGORITHM, SECRET_KEY
from app.core.security import (
    criar_token_acesso,
    decodificar_token,
    gerar_hash_senha,
    verificar_senha,
)


def test_hash_nao_guarda_a_senha_original():
    """O hash gerado é diferente da senha e segue o formato bcrypt."""
    senha_hash = gerar_hash_senha("solar12345")
    assert senha_hash != "solar12345"
    assert senha_hash.startswith("$2")


def test_hash_da_mesma_senha_muda_a_cada_chamada():
    """O bcrypt usa um salt aleatório, então dois hashes da mesma senha são diferentes."""
    assert gerar_hash_senha("solar12345") != gerar_hash_senha("solar12345")


def test_verificar_senha_correta():
    senha_hash = gerar_hash_senha("solar12345")
    assert verificar_senha("solar12345", senha_hash) is True


def test_verificar_senha_incorreta():
    senha_hash = gerar_hash_senha("solar12345")
    assert verificar_senha("senha-errada", senha_hash) is False


def test_token_guarda_email_no_campo_sub():
    """O token gerado é decodificado de volta para o email do usuário."""
    token = criar_token_acesso("operacao@bulbe.com.br")
    assert decodificar_token(token) == "operacao@bulbe.com.br"


def test_token_tem_data_de_expiracao():
    token = criar_token_acesso("operacao@bulbe.com.br", expira_em=timedelta(minutes=5))
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["exp"] - payload["iat"] == 5 * 60


def test_token_expirado_e_rejeitado():
    """Um token com validade negativa já nasce expirado."""
    token = criar_token_acesso("operacao@bulbe.com.br", expira_em=timedelta(minutes=-1))
    with pytest.raises(jwt.ExpiredSignatureError):
        decodificar_token(token)


def test_token_assinado_com_outra_chave_e_rejeitado():
    """Um token forjado com outra chave secreta não passa na validação da assinatura."""
    outra_chave = "outra-chave-secreta-com-pelo-menos-32-bytes"
    token_forjado = jwt.encode({"sub": "invasor@email.com"}, outra_chave, algorithm=ALGORITHM)
    with pytest.raises(jwt.InvalidSignatureError):
        decodificar_token(token_forjado)


def test_token_malformado_e_rejeitado():
    with pytest.raises(jwt.PyJWTError):
        decodificar_token("isto-nao-e-um-jwt")
