"""
Camada de Seguranca do Painel, autenticacao do funcionario por token assinado.

Token no formato "<payload>.<assinatura>", ambos em base64url sem padding:
- payload: JSON com id, nome, email, perfil, iat e exp (epoch em segundos);
- assinatura: HMAC-SHA256 do payload codificado, com o segredo PAINEL_SECRET.

Usa somente a biblioteca padrao + FastAPI (sem PyJWT). O token expira em 8 horas
e e guardado pela interface no sessionStorage do navegador.
"""
import base64
import binascii
import hashlib
import hmac
import json
import logging
import os
import time

from fastapi import Depends, Header, HTTPException, status

logger = logging.getLogger(__name__)

# Segredo usado apenas em desenvolvimento. Em qualquer outro ambiente defina PAINEL_SECRET.
SEGREDO_PADRAO_DESENVOLVIMENTO = "bulbe-painel-segredo-de-desenvolvimento-troque-em-producao"
DURACAO_TOKEN_SEGUNDOS = 8 * 60 * 60
CAMPOS_FUNCIONARIO = ("id", "nome", "email", "perfil")
PERFIL_ADMIN = "admin"
TAMANHO_MAXIMO_TOKEN = 4096

_aviso_segredo_emitido = False


def _obter_segredo() -> bytes:
    """Le o segredo do ambiente a cada uso (permite carregar o .env depois do import)."""
    global _aviso_segredo_emitido
    segredo = os.getenv("PAINEL_SECRET")
    if not segredo:
        if not _aviso_segredo_emitido:
            logger.warning(
                "PAINEL_SECRET nao definido: usando o segredo padrao de desenvolvimento. "
                "Defina PAINEL_SECRET antes de publicar o painel."
            )
            _aviso_segredo_emitido = True
        segredo = SEGREDO_PADRAO_DESENVOLVIMENTO
    return segredo.encode("utf-8")


def _codificar_base64url(dados: bytes) -> str:
    """Codifica em base64url sem o padding '='."""
    return base64.urlsafe_b64encode(dados).rstrip(b"=").decode("ascii")


def _decodificar_base64url(texto: str) -> bytes:
    """Decodifica base64url aceitando a ausencia de padding. Levanta ValueError se invalido."""
    padding = "=" * (-len(texto) % 4)
    return base64.urlsafe_b64decode((texto + padding).encode("ascii"))


def _assinar(corpo: str) -> bytes:
    """Calcula o HMAC-SHA256 do payload ja codificado."""
    return hmac.new(_obter_segredo(), corpo.encode("ascii"), hashlib.sha256).digest()


def _erro(code: str, message: str, status_http: int) -> HTTPException:
    """Monta a HTTPException com o detail no formato padrao do projeto."""
    headers = {"WWW-Authenticate": "Bearer"} if status_http == status.HTTP_401_UNAUTHORIZED else None
    return HTTPException(
        status_code=status_http,
        detail={"error": {"code": code, "message": message, "status": status_http}},
        headers=headers,
    )


def criar_token(funcionario: dict) -> str:
    """Gera o token assinado do funcionario, valido por 8 horas."""
    agora = int(time.time())
    payload = {campo: funcionario.get(campo) for campo in CAMPOS_FUNCIONARIO}
    payload["iat"] = agora
    payload["exp"] = agora + DURACAO_TOKEN_SEGUNDOS
    corpo = _codificar_base64url(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    )
    assinatura = _codificar_base64url(_assinar(corpo))
    return f"{corpo}.{assinatura}"


def validar_token(token: str) -> dict | None:
    """Confere assinatura e validade. Devolve {id, nome, email, perfil} ou None."""
    if not isinstance(token, str) or not token or len(token) > TAMANHO_MAXIMO_TOKEN:
        return None
    partes = token.split(".")
    if len(partes) != 2 or not partes[0] or not partes[1]:
        return None
    corpo, assinatura_recebida = partes
    try:
        assinatura = _decodificar_base64url(assinatura_recebida)
        esperada = _assinar(corpo)
        if not hmac.compare_digest(assinatura, esperada):
            return None
        payload = json.loads(_decodificar_base64url(corpo).decode("utf-8"))
    except (ValueError, binascii.Error, UnicodeError):
        # json.JSONDecodeError e subclasse de ValueError.
        return None

    if not isinstance(payload, dict):
        return None
    expira_em = payload.get("exp")
    if not isinstance(expira_em, int) or isinstance(expira_em, bool) or expira_em <= int(time.time()):
        return None
    if any(payload.get(campo) in (None, "") for campo in CAMPOS_FUNCIONARIO):
        return None
    return {campo: payload[campo] for campo in CAMPOS_FUNCIONARIO}


def funcionario_logado(authorization: str | None = Header(default=None)) -> dict:
    """Dependencia FastAPI: exige o cabecalho "Authorization: Bearer <token>" valido."""
    if not authorization:
        raise _erro(
            "NAO_AUTENTICADO",
            "Faca login no painel para continuar.",
            status.HTTP_401_UNAUTHORIZED,
        )
    esquema, _, token = authorization.strip().partition(" ")
    if esquema.lower() != "bearer" or not token.strip():
        raise _erro(
            "NAO_AUTENTICADO",
            "Cabecalho Authorization deve ser 'Bearer <token>'.",
            status.HTTP_401_UNAUTHORIZED,
        )
    funcionario = validar_token(token.strip())
    if funcionario is None:
        raise _erro(
            "TOKEN_INVALIDO",
            "Sessao invalida ou expirada. Faca login novamente.",
            status.HTTP_401_UNAUTHORIZED,
        )
    return funcionario


def exigir_admin(funcionario: dict = Depends(funcionario_logado)) -> dict:
    """Dependencia FastAPI: permite apenas funcionarios com perfil admin."""
    if funcionario.get("perfil") != PERFIL_ADMIN:
        raise _erro(
            "ACESSO_NEGADO",
            "Esta acao e permitida apenas para administradores.",
            status.HTTP_403_FORBIDDEN,
        )
    return funcionario
