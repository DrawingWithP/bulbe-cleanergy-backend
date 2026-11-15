"""
Cliente HTTP da API do app (backend), usado pelo painel para escrever no app.

Hoje cobre uma operacao: alterar a etapa de ativacao de um cliente
(PATCH /v1/clientes/{id}/ativacao, protegido por JWT de operador). O token e obtido
com o operador configurado (INTEGRACAO_APP_API_EMAIL/SENHA) e reaproveitado ate expirar.

Usa so a biblioteca padrao (urllib), sem dependencia nova.
"""
from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from app.integracao.config import ConfigIntegracao, obter_config

TIMEOUT_SEGUNDOS = 10
VALIDADE_TOKEN_SEGUNDOS = 20 * 60  # o backend emite tokens de 30 min por padrao

_trava = threading.Lock()
_token: dict[str, Any] = {"valor": None, "expira": 0.0, "chave": None}


class ErroApiApp(Exception):
    """Falha ao falar com a API do app, ja no formato de erro do painel."""

    def __init__(self, code: str, message: str, status: int) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


def _requisitar(
    metodo: str, url: str, *, corpo: bytes | None = None, cabecalhos: dict[str, str] | None = None
) -> tuple[int, Any]:
    requisicao = urllib.request.Request(url, data=corpo, method=metodo, headers=cabecalhos or {})
    try:
        with urllib.request.urlopen(requisicao, timeout=TIMEOUT_SEGUNDOS) as resposta:  # noqa: S310 - URL da config
            bruto = resposta.read()
            return resposta.status, json.loads(bruto) if bruto else None
    except urllib.error.HTTPError as erro:
        bruto = erro.read()
        try:
            conteudo = json.loads(bruto) if bruto else None
        except ValueError:
            conteudo = None
        return erro.code, conteudo
    except (urllib.error.URLError, TimeoutError, OSError) as erro:
        raise ErroApiApp(
            "APP_INDISPONIVEL",
            "A API do app nao respondeu. Confira se o backend esta rodando "
            f"(INTEGRACAO_APP_API_URL). Detalhe: {getattr(erro, 'reason', erro)}",
            503,
        ) from erro


def _mensagem(conteudo: Any, padrao: str) -> str:
    if isinstance(conteudo, dict):
        if isinstance(conteudo.get("error"), dict) and conteudo["error"].get("message"):
            return str(conteudo["error"]["message"])
        if isinstance(conteudo.get("detail"), list) and conteudo["detail"]:
            return str(conteudo["detail"][0].get("msg") or padrao)
        if conteudo.get("detail"):
            return str(conteudo["detail"])
    return padrao


def _obter_token(cfg: ConfigIntegracao, renovar: bool = False) -> str:
    chave = (cfg.api_url, cfg.api_email)
    with _trava:
        if not renovar and _token["valor"] and _token["chave"] == chave and time.monotonic() < _token["expira"]:
            return str(_token["valor"])
        corpo = urllib.parse.urlencode({"username": cfg.api_email, "password": cfg.api_senha}).encode()
        status, conteudo = _requisitar(
            "POST", f"{cfg.api_url}/v1/auth/login", corpo=corpo,
            cabecalhos={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
        )
        if status != 200 or not isinstance(conteudo, dict) or not conteudo.get("access_token"):
            raise ErroApiApp(
                "APP_CREDENCIAIS_INVALIDAS",
                "O painel nao conseguiu entrar na API do app com o operador configurado "
                "(INTEGRACAO_APP_API_EMAIL/INTEGRACAO_APP_API_SENHA).",
                502,
            )
        _token.update(valor=conteudo["access_token"], expira=time.monotonic() + VALIDADE_TOKEN_SEGUNDOS, chave=chave)
        return str(conteudo["access_token"])


def limpar_token() -> None:
    """Esquece o token guardado (testes)."""
    with _trava:
        _token.update(valor=None, expira=0.0, chave=None)


def alterar_etapa_ativacao(
    id_cliente_app: str, etapa: int, observacao: str | None = None, config: ConfigIntegracao | None = None
) -> dict:
    """PATCH /v1/clientes/{id}/ativacao no app. Devolve a resposta da API."""
    cfg = config or obter_config()
    url = f"{cfg.api_url}/v1/clientes/{urllib.parse.quote(id_cliente_app, safe='')}/ativacao"
    corpo = json.dumps({"etapa_atual": etapa, **({"observacao": observacao} if observacao else {})}).encode()

    for tentativa in range(2):
        token = _obter_token(cfg, renovar=tentativa > 0)
        status, conteudo = _requisitar(
            "PATCH", url, corpo=corpo,
            cabecalhos={"Content-Type": "application/json", "Accept": "application/json",
                        "Authorization": f"Bearer {token}"},
        )
        if status == 401 and tentativa == 0:
            continue  # token expirado: renova uma vez
        break

    if status == 200 and isinstance(conteudo, dict):
        return conteudo
    if status == 404:
        raise ErroApiApp("CLIENTE_NAO_ENCONTRADO_NO_APP", _mensagem(conteudo, "Cliente nao encontrado no app."), 404)
    if status in (400, 409, 422):
        raise ErroApiApp("ATIVACAO_INVALIDA", _mensagem(conteudo, "O app recusou a mudanca de etapa."), 422)
    raise ErroApiApp("APP_ERRO", _mensagem(conteudo, f"A API do app respondeu {status}."), 502)
