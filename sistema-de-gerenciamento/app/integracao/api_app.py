"""
Cliente HTTP da API do app (backend), usado pelo painel para escrever no app.

Operacoes: alterar a etapa de ativacao, controlar o relogio de demonstracao
e as demais acoes de operador (dicas, parceiros, catalogo de cupons, adesoes e
atendimentos). As rotas protegidas usam um token JWT obtido com o operador
configurado (INTEGRACAO_APP_API_EMAIL/SENHA), reaproveitado ate expirar.

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


def _codigo(conteudo: Any) -> str | None:
    if isinstance(conteudo, dict) and isinstance(conteudo.get("error"), dict):
        return conteudo["error"].get("code")
    return None


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


def chamar(
    metodo: str,
    caminho: str,
    corpo: Any = None,
    *,
    autenticado: bool = True,
    config: ConfigIntegracao | None = None,
) -> Any:
    """
    Chama a API do app e devolve o JSON da resposta (None para 204).
    Erros viram ErroApiApp com o codigo e a mensagem do app; 401 renova o token uma vez.
    """
    cfg = config or obter_config()
    url = f"{cfg.api_url}{caminho}"
    dados = json.dumps(corpo).encode() if corpo is not None else None

    status, conteudo = 0, None
    for tentativa in range(2):
        cabecalhos = {"Accept": "application/json"}
        if dados is not None:
            cabecalhos["Content-Type"] = "application/json"
        if autenticado:
            cabecalhos["Authorization"] = f"Bearer {_obter_token(cfg, renovar=tentativa > 0)}"
        status, conteudo = _requisitar(metodo, url, corpo=dados, cabecalhos=cabecalhos)
        if status == 401 and autenticado and tentativa == 0:
            continue  # token expirado: renova uma vez
        break

    if 200 <= status < 300:
        return conteudo
    if status == 404:
        raise ErroApiApp(_codigo(conteudo) or "NAO_ENCONTRADO_NO_APP",
                         _mensagem(conteudo, "Registro nao encontrado no app."), 404)
    if status in (400, 409, 422):
        raise ErroApiApp(_codigo(conteudo) or "REQUISICAO_INVALIDA",
                         _mensagem(conteudo, "O app recusou a operacao."), 422 if status == 400 else status)
    raise ErroApiApp("APP_ERRO", _mensagem(conteudo, f"A API do app respondeu {status}."), 502)


def _id(valor: str) -> str:
    return urllib.parse.quote(str(valor), safe="")


# ---------------------------------------------------------------------------
# Operacoes usadas pelo painel
# ---------------------------------------------------------------------------
def alterar_etapa_ativacao(
    id_cliente_app: str, etapa: int, observacao: str | None = None, config: ConfigIntegracao | None = None
) -> dict:
    """PATCH /v1/clientes/{id}/ativacao no app. Devolve a resposta da API."""
    corpo = {"etapa_atual": etapa, **({"observacao": observacao} if observacao else {})}
    try:
        return chamar("PATCH", f"/v1/clientes/{_id(id_cliente_app)}/ativacao", corpo, config=config)
    except ErroApiApp as erro:
        if erro.status == 404:
            raise ErroApiApp("CLIENTE_NAO_ENCONTRADO_NO_APP", erro.message, 404) from erro
        if erro.status in (409, 422):
            raise ErroApiApp("ATIVACAO_INVALIDA", erro.message, 422) from erro
        raise


def relogio() -> dict:
    """GET /v1/demonstracao/relogio (publico)."""
    return chamar("GET", "/v1/demonstracao/relogio", autenticado=False)


def avancar_relogio(dias: int) -> dict:
    return chamar("POST", "/v1/demonstracao/relogio/avancar", {"dias": dias})


def resetar_relogio() -> dict:
    return chamar("POST", "/v1/demonstracao/relogio/resetar")


# Parceiros do Clube (CRUD do app)
def criar_parceiro(dados: dict) -> dict:
    return chamar("POST", "/v1/parceiros", dados)


def atualizar_parceiro(parceiro_id: str, dados: dict) -> dict:
    return chamar("PUT", f"/v1/parceiros/{_id(parceiro_id)}", dados)


def remover_parceiro(parceiro_id: str) -> None:
    chamar("DELETE", f"/v1/parceiros/{_id(parceiro_id)}")


# Catalogo de cupons sorteados nas cartas
def listar_catalogo(parceiro_id: str | None = None) -> list:
    consulta = f"?parceiro_id={_id(parceiro_id)}" if parceiro_id else ""
    return chamar("GET", f"/v1/catalogo-cupons{consulta}")


def criar_modelo_cupom(dados: dict) -> dict:
    return chamar("POST", "/v1/catalogo-cupons", dados)


def atualizar_modelo_cupom(modelo_id: str, dados: dict) -> dict:
    return chamar("PATCH", f"/v1/catalogo-cupons/{_id(modelo_id)}", dados)


def remover_modelo_cupom(modelo_id: str) -> None:
    chamar("DELETE", f"/v1/catalogo-cupons/{_id(modelo_id)}")


# Dicas do app (acervo, vitrine e cadastro)
def listar_dicas_app() -> list:
    return chamar("GET", "/v1/dicas?todas=true", autenticado=False)


def definir_vitrine_dicas(ids: list[int]) -> list:
    return chamar("PUT", "/v1/dicas/vitrine", {"dicas": ids})


def criar_dica(dados: dict) -> dict:
    return chamar("POST", "/v1/dicas", dados)


def atualizar_dica(dica_id: int, dados: dict) -> dict:
    return chamar("PUT", f"/v1/dicas/{int(dica_id)}", dados)


def remover_dica(dica_id: int) -> None:
    chamar("DELETE", f"/v1/dicas/{int(dica_id)}")


# Atendimento (chat do app)
def conversa(atendimento_id: str, depois_de: int = 0) -> dict:
    return chamar("GET", f"/v1/atendimentos/{_id(atendimento_id)}?depois_de={int(depois_de)}", autenticado=False)


def responder_atendimento(atendimento_id: str, texto: str, atendente: str) -> dict:
    return chamar("POST", f"/v1/atendimentos/{_id(atendimento_id)}/respostas",
                  {"texto": texto, "atendente": atendente})


def encerrar_atendimento(atendimento_id: str) -> dict:
    return chamar("POST", f"/v1/atendimentos/{_id(atendimento_id)}/encerramento", {}, autenticado=False)


# Adesoes: analise do pedido de contratacao
def aprovar_adesao(adesao_id_app: str) -> dict:
    return chamar("POST", f"/v1/adesoes/{_id(adesao_id_app)}/aprovacao")


def recusar_adesao(adesao_id_app: str) -> dict:
    return chamar("POST", f"/v1/adesoes/{_id(adesao_id_app)}/recusa")
