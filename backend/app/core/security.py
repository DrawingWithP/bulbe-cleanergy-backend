"""
Funcoes de seguranca: hash de senha e geracao/leitura de tokens JWT.
Nenhuma dessas funcoes conhece FastAPI, banco ou regra de negocio.
"""

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import ACCESS_TOKEN_EXPIRE_MINUTES, ALGORITHM, SECRET_KEY


def gerar_hash_senha(senha: str) -> str:
    """Transforma a senha em um hash bcrypt. A senha original nunca e guardada."""
    return bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verificar_senha(senha: str, senha_hash: str) -> bool:
    """Confere se a senha digitada corresponde ao hash armazenado."""
    return bcrypt.checkpw(senha.encode("utf-8"), senha_hash.encode("utf-8"))


def criar_token_acesso(email: str, expira_em: timedelta | None = None) -> str:
    """Gera um JWT assinado com o email do usuario no campo 'sub'."""
    agora = datetime.now(timezone.utc)
    validade = expira_em if expira_em is not None else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": email,
        "iat": agora,
        "exp": agora + validade,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decodificar_token(token: str) -> str:
    """
    Valida assinatura e expiracao do token e devolve o email ('sub').
    Levanta jwt.PyJWTError se o token for invalido ou estiver expirado.
    """
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    return payload["sub"]