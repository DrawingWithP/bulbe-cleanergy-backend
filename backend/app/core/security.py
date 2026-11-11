"""
Funcoes de seguranca: hash de senha e geracao/leitura de tokens JWT.

Nenhuma dessas funcoes conhece FastAPI, banco de dados
ou regras de negocio.
"""

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    ALGORITHM,
    SECRET_KEY,
)


def gerar_hash_senha(
    senha: str,
) -> str:
    """
    Transforma a senha em um hash bcrypt.

    A senha original nunca e armazenada.
    """

    senha_bytes = senha.encode("utf-8")

    hash_bytes = bcrypt.hashpw(
        senha_bytes,
        bcrypt.gensalt(),
    )

    return hash_bytes.decode("utf-8")


def verificar_senha(
    senha: str,
    senha_hash: str,
) -> bool:
    """
    Verifica se a senha informada corresponde
    ao hash armazenado.
    """

    return bcrypt.checkpw(
        senha.encode("utf-8"),
        senha_hash.encode("utf-8"),
    )


def criar_token_acesso(
    email: str,
    expira_em: timedelta | None = None,
) -> str:
    """
    Gera um token JWT assinado.

    O email do usuario e armazenado no campo 'sub'.
    """

    agora = datetime.now(timezone.utc)

    validade = (
        expira_em
        if expira_em is not None
        else timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )
    )

    payload = {
        "sub": email,
        "iat": agora,
        "exp": agora + validade,
    }

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


def decodificar_token(
    token: str,
) -> str:
    """
    Valida a assinatura e a expiracao do JWT.

    Retorna o email armazenado no campo 'sub'.

    Levanta jwt.PyJWTError caso o token seja
    invalido, esteja expirado ou nao possua
    um subject valido.
    """

    payload = jwt.decode(
        token,
        SECRET_KEY,
        algorithms=[ALGORITHM],
    )

    email = payload.get("sub")

    if not isinstance(email, str) or not email:
        raise jwt.InvalidTokenError(
            "Token sem subject valido."
        )

    return email
