"""
Apoio aos testes: API da Anthropic simulada, SMTP simulado e funcoes utilitarias.

API da Anthropic simulada
-------------------------
O SDK oficial `anthropic` continua sendo usado de verdade (mesmas classes, mesmos erros,
mesmo acumulador de streaming), mas o cliente HTTP recebe um `httpx.MockTransport`.
Assim o teste nao depende de COMO o servico chama o SDK (`messages.create`,
`messages.stream`, cliente sincrono ou assincrono): toda requisicao para `/v1/messages`
e respondida a partir de um roteiro e o corpo enviado fica registrado em `api.chamadas`.
Nenhuma requisicao sai da maquina.
"""
from __future__ import annotations

import json
import re
import smtplib
import sys
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any

import anthropic

try:  # versoes recentes do SDK usam o pacote `httpx2` (API identica a do httpx)
    import httpx2 as httpx
except ImportError:  # pragma: no cover
    import httpx

ANTHROPIC_REAL = anthropic.Anthropic
ANTHROPIC_ASSINCRONO_REAL = anthropic.AsyncAnthropic

USO_PADRAO: dict[str, int] = {
    "input_tokens": 100,
    "output_tokens": 20,
    "cache_read_input_tokens": 0,
    "cache_creation_input_tokens": 0,
}

# Precos do contrato (US$ por milhao de tokens) para o Claude Haiku 5.5.
PRECO_ENTRADA = 0.10
PRECO_SAIDA = 0.50
PRECO_CACHE_LEITURA = PRECO_ENTRADA * 0.1
PRECO_CACHE_ESCRITA = PRECO_ENTRADA * 1.25


def custo_esperado(input_tokens: int, output_tokens: int, cache_read: int, cache_creation: int) -> float:
    """Custo estimado em US$ segundo a regra de precos do contrato (secao 2.2)."""
    return (
        input_tokens * PRECO_ENTRADA
        + output_tokens * PRECO_SAIDA
        + cache_read * PRECO_CACHE_LEITURA
        + cache_creation * PRECO_CACHE_ESCRITA
    ) / 1_000_000


# ---------------------------------------------------------------------------
# Roteiro de respostas
# ---------------------------------------------------------------------------
def _uso(uso: dict | None) -> dict:
    return {**USO_PADRAO, **(uso or {})}


def bloco_thinking(texto: str = "Vou consultar os dados antes de responder.") -> dict:
    return {"type": "thinking", "thinking": texto, "signature": "assinatura-falsa-" + uuid.uuid4().hex[:12]}


def resposta_texto(texto: str, *, uso: dict | None = None, stop_reason: str = "end_turn",
                   thinking: str | None = None) -> dict:
    """Resposta final do modelo (somente texto)."""
    conteudo: list[dict] = []
    if thinking:
        conteudo.append(bloco_thinking(thinking))
    conteudo.append({"type": "text", "text": texto})
    return {"tipo": "mensagem", "content": conteudo, "stop_reason": stop_reason, "usage": _uso(uso)}


def resposta_ferramentas(chamadas: list[tuple[str, dict]], *, texto: str | None = None,
                         thinking: str | None = None, uso: dict | None = None) -> dict:
    """Resposta com stop_reason tool_use pedindo uma ou mais ferramentas."""
    conteudo: list[dict] = []
    if thinking:
        conteudo.append(bloco_thinking(thinking))
    if texto:
        conteudo.append({"type": "text", "text": texto})
    for nome, entrada in chamadas:
        conteudo.append({
            "type": "tool_use",
            "id": "toolu_teste_" + uuid.uuid4().hex[:16],
            "name": nome,
            "input": entrada,
        })
    return {"tipo": "mensagem", "content": conteudo, "stop_reason": "tool_use", "usage": _uso(uso)}


def resposta_erro(status: int, tipo: str = "api_error", mensagem: str = "erro simulado") -> dict:
    """Erro HTTP da API (o SDK transforma em RateLimitError, APIStatusError etc.)."""
    return {"tipo": "erro", "status": status, "erro_tipo": tipo, "mensagem": mensagem}


def resposta_falha_conexao() -> dict:
    """Falha de rede (o SDK transforma em APIConnectionError)."""
    return {"tipo": "conexao"}


class ApiAnthropicFalsa:
    """Servidor falso da API de mensagens, alimentado por um roteiro de respostas."""

    def __init__(self) -> None:
        self.roteiro: list[dict] = []
        self.padrao: dict | None = None
        self.chamadas: list[dict] = []
        self.respostas_enviadas: list[dict] = []

    def adicionar(self, *respostas: dict) -> None:
        self.roteiro.extend(respostas)

    def _proxima(self) -> dict:
        if self.roteiro:
            return self.roteiro.pop(0)
        if self.padrao is not None:
            return self.padrao
        return resposta_texto("ROTEIRO ESGOTADO")

    # Chamado pelo httpx.MockTransport (sincrono e assincrono).
    def tratar(self, requisicao: httpx.Request) -> httpx.Response:
        caminho = requisicao.url.path
        if caminho.endswith("/count_tokens"):
            return httpx.Response(200, json={"input_tokens": 10})
        if not caminho.endswith("/messages"):
            return httpx.Response(404, json={"type": "error", "error": {"type": "not_found_error",
                                                                        "message": "rota simulada inexistente"}})
        corpo = json.loads(requisicao.read() or b"{}")
        self.chamadas.append(corpo)
        especificacao = self._proxima()

        if especificacao["tipo"] == "conexao":
            raise httpx.ConnectError("conexao recusada (simulada)", request=requisicao)
        if especificacao["tipo"] == "erro":
            return httpx.Response(
                especificacao["status"],
                json={"type": "error", "error": {"type": especificacao["erro_tipo"],
                                                 "message": especificacao["mensagem"]}},
                headers={"request-id": "req_teste"},
            )

        mensagem = {
            "id": "msg_teste_" + uuid.uuid4().hex[:16],
            "type": "message",
            "role": "assistant",
            "model": corpo.get("model", "claude-haiku-5-5"),
            "content": especificacao["content"],
            "stop_reason": especificacao["stop_reason"],
            "stop_sequence": None,
            "usage": especificacao["usage"],
        }
        self.respostas_enviadas.append(mensagem)
        if corpo.get("stream"):
            return httpx.Response(
                200,
                headers={"content-type": "text/event-stream", "request-id": "req_teste"},
                content=_montar_sse(mensagem),
            )
        return httpx.Response(200, json=mensagem, headers={"request-id": "req_teste"})


def _pedacos(texto: str, tamanho: int) -> list[str]:
    return [texto[i:i + tamanho] for i in range(0, len(texto), tamanho)] or [""]


def _montar_sse(mensagem: dict) -> bytes:
    """Converte uma mensagem completa nos eventos SSE da API de streaming."""
    uso = mensagem["usage"]
    eventos: list[tuple[str, dict]] = [(
        "message_start",
        {"type": "message_start", "message": {**mensagem, "content": [], "stop_reason": None,
                                              "stop_sequence": None, "usage": {**uso, "output_tokens": 1}}},
    )]
    for indice, bloco in enumerate(mensagem["content"]):
        if bloco["type"] == "text":
            inicio = {"type": "text", "text": ""}
            deltas = [{"type": "text_delta", "text": p} for p in _pedacos(bloco["text"], 6)]
        elif bloco["type"] == "thinking":
            inicio = {"type": "thinking", "thinking": "", "signature": ""}
            deltas = [{"type": "thinking_delta", "thinking": p} for p in _pedacos(bloco["thinking"], 10)]
            deltas.append({"type": "signature_delta", "signature": bloco["signature"]})
        elif bloco["type"] == "tool_use":
            inicio = {"type": "tool_use", "id": bloco["id"], "name": bloco["name"], "input": {}}
            deltas = [{"type": "input_json_delta", "partial_json": p}
                      for p in _pedacos(json.dumps(bloco["input"], ensure_ascii=False), 5)]
        else:  # pragma: no cover
            raise ValueError(bloco["type"])
        eventos.append(("content_block_start",
                        {"type": "content_block_start", "index": indice, "content_block": inicio}))
        for delta in deltas:
            eventos.append(("content_block_delta",
                            {"type": "content_block_delta", "index": indice, "delta": delta}))
        eventos.append(("content_block_stop", {"type": "content_block_stop", "index": indice}))
    eventos.append(("message_delta", {
        "type": "message_delta",
        "delta": {"stop_reason": mensagem["stop_reason"], "stop_sequence": None},
        "usage": dict(uso),
    }))
    eventos.append(("message_stop", {"type": "message_stop"}))
    return "".join(
        f"event: {tipo}\ndata: {json.dumps(dados, ensure_ascii=False)}\n\n" for tipo, dados in eventos
    ).encode("utf-8")


def limpar_clientes_em_cache(monkeypatch) -> None:
    """Zera clientes da Anthropic guardados em objetos/modulos do pacote app.chatbot."""
    for nome_modulo, modulo in list(sys.modules.items()):
        if not nome_modulo.startswith("app.chatbot") or modulo is None:
            continue
        for nome_attr, valor in list(vars(modulo).items()):
            if isinstance(valor, (ANTHROPIC_REAL, ANTHROPIC_ASSINCRONO_REAL)):
                monkeypatch.setattr(modulo, nome_attr, None)
                continue
            classe = type(valor)
            if getattr(classe, "__module__", "").startswith("app.chatbot") and hasattr(valor, "__dict__"):
                for nome_interno, valor_interno in list(vars(valor).items()):
                    if isinstance(valor_interno, (ANTHROPIC_REAL, ANTHROPIC_ASSINCRONO_REAL)):
                        monkeypatch.setattr(valor, nome_interno, None)
                    elif ("client" in nome_interno.lower() or "chave" in nome_interno.lower()) \
                            and not callable(valor_interno):
                        monkeypatch.setattr(valor, nome_interno, None)


def criar_cliente_falso(api: ApiAnthropicFalsa) -> Any:
    """Cliente do SDK real (classe original) cujo transporte HTTP e a API simulada."""
    return ANTHROPIC_REAL(
        api_key="sk-ant-teste-falsa",
        http_client=httpx.Client(transport=httpx.MockTransport(api.tratar)),
        max_retries=0,
    )


def injetar_api_falsa(api: ApiAnthropicFalsa) -> None:
    """Injeta no servico do chatbot um cliente que fala com `api` (chatbot_service.definir_cliente)."""
    from app.chatbot.servico import chatbot_service

    assert hasattr(chatbot_service, "definir_cliente"), "O servico precisa expor definir_cliente(cliente)."
    chatbot_service.definir_cliente(criar_cliente_falso(api))


def remover_api_falsa() -> None:
    from app.chatbot.servico import chatbot_service

    chatbot_service.definir_cliente(None)


class GuardaInstanciacao:
    """Registra qualquer tentativa de criar um cliente real da Anthropic durante um teste."""

    def __init__(self) -> None:
        self.tentativas: list[str] = []


def instalar_guarda_anthropic(monkeypatch) -> GuardaInstanciacao:
    """
    Substitui anthropic.Anthropic/AsyncAnthropic por classes que recusam a criacao
    (e registram a tentativa). Assim nenhum teste consegue chamar a API paga por acidente.
    """
    guarda = GuardaInstanciacao()

    def _fabrica(nome: str):
        def _recusar(*_: Any, **__: Any) -> Any:
            guarda.tentativas.append(nome)
            raise RuntimeError(f"Teste tentou criar anthropic.{nome} de verdade (proibido nos testes).")
        return _recusar

    monkeypatch.setattr(anthropic, "Anthropic", _fabrica("Anthropic"))
    monkeypatch.setattr(anthropic, "AsyncAnthropic", _fabrica("AsyncAnthropic"))
    for nome_modulo, modulo in list(sys.modules.items()):
        if not nome_modulo.startswith("app.") or modulo is None:
            continue
        if getattr(modulo, "Anthropic", None) is ANTHROPIC_REAL:
            monkeypatch.setattr(modulo, "Anthropic", _fabrica("Anthropic"))
        if getattr(modulo, "AsyncAnthropic", None) is ANTHROPIC_ASSINCRONO_REAL:
            monkeypatch.setattr(modulo, "AsyncAnthropic", _fabrica("AsyncAnthropic"))
    return guarda


# ---------------------------------------------------------------------------
# Leitura das requisicoes enviadas a API
# ---------------------------------------------------------------------------
def sem_nulos(valor: Any) -> Any:
    """Remove recursivamente chaves com valor None (o SDK pode serializar campos opcionais nulos)."""
    if isinstance(valor, dict):
        return {k: sem_nulos(v) for k, v in valor.items() if v is not None}
    if isinstance(valor, list):
        return [sem_nulos(v) for v in valor]
    return valor


def texto_do_conteudo(conteudo: Any) -> str:
    """Texto de um `content` (string ou lista de blocos)."""
    if isinstance(conteudo, str):
        return conteudo
    partes = []
    for bloco in conteudo or []:
        if isinstance(bloco, dict) and bloco.get("type") == "text":
            partes.append(bloco.get("text", ""))
    return "\n".join(partes)


def conteudo_como_blocos(conteudo: Any) -> list[dict]:
    """Normaliza `content` para lista de blocos (string vira um bloco de texto)."""
    if isinstance(conteudo, str):
        return [{"type": "text", "text": conteudo}]
    return list(conteudo or [])


def resultados_de_ferramenta(mensagem: dict) -> list[dict]:
    return [b for b in conteudo_como_blocos(mensagem.get("content")) if b.get("type") == "tool_result"]


def texto_do_tool_result(bloco: dict) -> str:
    conteudo = bloco.get("content")
    if isinstance(conteudo, str):
        return conteudo
    return texto_do_conteudo(conteudo)


# ---------------------------------------------------------------------------
# Streaming (SSE) do chat
# ---------------------------------------------------------------------------
def ler_eventos_sse(corpo: str) -> list[dict]:
    """Extrai os eventos `data: <json>` de uma resposta text/event-stream."""
    eventos: list[dict] = []
    for bloco in re.split(r"\r?\n\r?\n", corpo):
        linhas_dados = [linha[5:].lstrip() for linha in bloco.splitlines() if linha.startswith("data:")]
        if not linhas_dados:
            continue
        eventos.append(json.loads("\n".join(linhas_dados)))
    return eventos


# ---------------------------------------------------------------------------
# Datas
# ---------------------------------------------------------------------------
def agora_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)


def datas_de_hoje_aceitas() -> set[str]:
    """Data de hoje em dd/mm/aaaa (local e UTC, para nao falhar perto da meia-noite)."""
    return {date.today().strftime("%d/%m/%Y"), agora_utc().date().strftime("%d/%m/%Y")}


def dias_atras(dias: float) -> datetime:
    return agora_utc() - timedelta(days=dias)


# ---------------------------------------------------------------------------
# SMTP simulado
# ---------------------------------------------------------------------------
class RegistroSmtp:
    """Guarda as conexoes e mensagens feitas pelo SMTP simulado."""

    def __init__(self) -> None:
        self.conexoes: list[dict] = []
        self.mensagens: list[Any] = []
        self.falhar_com: Exception | None = None


def instalar_smtp_falso(monkeypatch) -> RegistroSmtp:
    registro = RegistroSmtp()

    class SmtpFalso:
        def __init__(self, host: str = "", port: int = 0, *args: Any, **kwargs: Any) -> None:
            self.host, self.port = host, port
            registro.conexoes.append({"host": host, "porta": port, "ssl": False})
            if registro.falhar_com is not None:
                raise registro.falhar_com

        def __enter__(self) -> "SmtpFalso":
            return self

        def __exit__(self, *exc: Any) -> None:
            return None

        def set_debuglevel(self, *_: Any) -> None: ...
        def ehlo(self, *_: Any, **__: Any) -> tuple[int, bytes]: return (250, b"ok")
        def ehlo_or_helo_if_needed(self) -> None: ...
        def has_extn(self, *_: Any) -> bool: return True
        def starttls(self, *_: Any, **__: Any) -> tuple[int, bytes]: return (220, b"ok")
        def login(self, *_: Any, **__: Any) -> tuple[int, bytes]: return (235, b"ok")
        def connect(self, *_: Any, **__: Any) -> tuple[int, bytes]: return (220, b"ok")
        def noop(self) -> tuple[int, bytes]: return (250, b"ok")

        def send_message(self, mensagem: Any, from_addr: Any = None, to_addrs: Any = None, **_: Any) -> dict:
            registro.mensagens.append(mensagem)
            return {}

        def sendmail(self, from_addr: Any, to_addrs: Any, mensagem: Any, *_: Any, **__: Any) -> dict:
            registro.mensagens.append(mensagem)
            return {}

        def quit(self) -> tuple[int, bytes]: return (221, b"bye")
        def close(self) -> None: ...

    class SmtpSslFalso(SmtpFalso):
        def __init__(self, host: str = "", port: int = 0, *args: Any, **kwargs: Any) -> None:
            super().__init__(host, port, *args, **kwargs)
            registro.conexoes[-1]["ssl"] = True

    monkeypatch.setattr(smtplib, "SMTP", SmtpFalso)
    monkeypatch.setattr(smtplib, "SMTP_SSL", SmtpSslFalso)
    for nome_modulo, modulo in list(sys.modules.items()):
        if not nome_modulo.startswith("app.") or modulo is None:
            continue
        if getattr(modulo, "SMTP", None) is not None and nome_modulo != "smtplib":
            monkeypatch.setattr(modulo, "SMTP", SmtpFalso, raising=False)
        if getattr(modulo, "SMTP_SSL", None) is not None:
            monkeypatch.setattr(modulo, "SMTP_SSL", SmtpSslFalso, raising=False)
    return registro


def aplicar_config_smtp(monkeypatch, valores: dict[str, str]) -> None:
    """
    Define as variaveis de SMTP/alerta no ambiente e, se o modulo de alertas guardar
    constantes com os mesmos nomes (lidas no import), atualiza tambem essas constantes.
    """
    for chave, valor in valores.items():
        monkeypatch.setenv(chave, valor)
    for nome_modulo, modulo in list(sys.modules.items()):
        if not nome_modulo.startswith("app.painel") or modulo is None:
            continue
        for chave, valor in valores.items():
            if hasattr(modulo, chave):
                atual = getattr(modulo, chave)
                if isinstance(atual, bool):
                    convertido: Any = valor.strip().lower() in ("1", "true", "sim", "yes")
                elif isinstance(atual, int):
                    convertido = int(valor)
                else:
                    convertido = valor
                monkeypatch.setattr(modulo, chave, convertido)


def texto_do_email(mensagem: Any) -> str:
    """Assunto + destinatarios + corpo de uma EmailMessage (ou string/bytes) para inspecao."""
    if isinstance(mensagem, bytes):
        return mensagem.decode("utf-8", errors="replace")
    if isinstance(mensagem, str):
        return mensagem
    partes = [str(mensagem.get("Subject", "")), str(mensagem.get("To", "")), str(mensagem.get("From", ""))]
    if mensagem.is_multipart():
        for parte in mensagem.walk():
            if parte.get_content_maintype() == "text":
                partes.append(parte.get_content())
    else:
        try:
            partes.append(mensagem.get_content())
        except Exception:  # noqa: BLE001 - email.message.Message antigo
            partes.append(str(mensagem.get_payload(decode=True) or b"", "utf-8", "replace"))
    return "\n".join(partes)
