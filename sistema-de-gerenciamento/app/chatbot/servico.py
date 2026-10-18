"""
Camada de Servico, ChatbotService.

Conversa com o Claude (SDK oficial `anthropic`) usando um loop MANUAL de tool use:
1. envia system + tools + historico + pergunta;
2. enquanto stop_reason == "tool_use", executa TODAS as ferramentas pedidas
   e devolve TODOS os tool_result numa unica mensagem "user";
3. termina em "end_turn" (ou trata "max_tokens", "refusal" e "pause_turn").

Dois modos com o mesmo nucleo (`executar`, um gerador de eventos):
- sincrono (`responder`): cada volta com `client.messages.create(...)`;
- streaming (`executar(..., ao_vivo=True)`): cada volta com `client.messages.stream(...)`,
  emitindo os pedacos de texto e as ferramentas chamadas enquanto o modelo gera.

Historico no servidor ("preserved thinking" do Claude Haiku 5.5):
- cada mensagem enviada/recebida da API e guardada com o conteudo EXATO
  (blocos serializados com `to_dict()`, inclusive `thinking`) e reenviada igual;
- o historico e so de acrescimo: nada e editado, reordenado ou removido;
- o `system` e o `tools` sao identicos byte a byte em toda a conversa; a data de
  hoje e o funcionario vao no inicio do texto de cada nova pergunta;
- o turno inteiro (pergunta, voltas de ferramenta e resposta final) so e gravado
  quando termina, para o historico nunca ficar com um tool_use sem tool_result.

Sem `conversa_id` e com `historico` de texto (v1), o historico e convertido como
antes e gravado numa conversa nova junto com a troca atual.
"""
import copy
import logging
import time
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Generator, Iterator

from app.chatbot import config
from app.chatbot.ferramentas import TOOLS, executar_ferramenta
from app.chatbot.prompts import PROMPT_SISTEMA, montar_mensagem_usuario
from app.database import consultas
from app.database.consultas import registrar_chat
from app.erros import ErroDeNegocio

try:
    import anthropic
except ImportError:  # o resto da API continua funcionando sem o SDK
    anthropic = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

MAX_MENSAGENS_HISTORICO: int = 20

MENSAGEM_RECUSA: str = (
    "Não posso ajudar com esse pedido. Posso consultar dados de clientes da Bulbe "
    "ou explicar o funcionamento do app — tente reformular a pergunta."
)
AVISO_MAX_TOKENS: str = (
    "\n\n_(Resposta interrompida por limite de tamanho. Peça para eu continuar "
    "ou faça uma pergunta mais específica.)_"
)
MENSAGEM_LIMITE_VOLTAS: str = (
    "Não consegui concluir a resposta dentro do limite de consultas desta pergunta. "
    "Tente dividir a pergunta em partes menores ou ser mais específico (ex.: informe o nome completo do cliente)."
)
MENSAGEM_SEM_TEXTO: str = "Não consegui gerar uma resposta agora. Tente reformular a pergunta."
MENSAGEM_FERRAMENTA_NAO_EXECUTADA: str = (
    "Consulta nao executada: a resposta anterior foi interrompida antes de a ferramenta rodar."
)

SEPARADOR_TEXTO: str = "\n\n"

_PAPEIS: dict[str, str] = {"funcionario": "user", "assistente": "assistant"}
_TIPOS_RACIOCINIO: frozenset[str] = frozenset({"thinking", "redacted_thinking"})


# ---------------------------------------------------------------------------
# Estruturas auxiliares
# ---------------------------------------------------------------------------
@dataclass
class UsoAcumulado:
    """Soma do `usage` de todas as voltas de uma pergunta e o custo estimado em USD."""

    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    custo_estimado_usd: float = 0.0

    def somar(self, usage: Any) -> None:
        """Soma o `usage` de uma resposta da API (campos ausentes ou None contam como 0)."""
        if usage is None:
            return
        entrada = _inteiro(getattr(usage, "input_tokens", 0))
        saida = _inteiro(getattr(usage, "output_tokens", 0))
        cache_leitura = _inteiro(getattr(usage, "cache_read_input_tokens", 0))
        cache_escrita = _inteiro(getattr(usage, "cache_creation_input_tokens", 0))
        self.input_tokens += entrada
        self.output_tokens += saida
        self.cache_read_tokens += cache_leitura
        self.cache_creation_tokens += cache_escrita
        self.custo_estimado_usd += estimar_custo_usd(entrada, saida, cache_leitura, cache_escrita)

    def como_dict(self) -> dict:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cache_read_tokens": self.cache_read_tokens,
            "cache_creation_tokens": self.cache_creation_tokens,
            "custo_estimado_usd": round(self.custo_estimado_usd, 6),
        }


@dataclass
class ContextoPergunta:
    """Tudo o que uma pergunta precisa, ja validado, antes de chamar a API."""

    cliente: Any
    funcionario: dict
    pergunta: str
    conversa_id: str | None
    # Mensagens anteriores no formato da API ({role, content}), reenviadas exatamente iguais.
    historico_api: list[dict] = field(default_factory=list)
    # Mensagens anteriores que ainda nao estao gravadas (historico de texto da v1).
    pendentes_gravacao: list[dict] = field(default_factory=list)
    # Se False, nao grava a conversa nem registra a troca (usado pelas avaliacoes).
    persistir: bool = True
    hoje: date | None = None


@dataclass
class _EstadoTurno:
    """Estado compartilhado entre as voltas de uma pergunta."""

    ja_emitiu_texto: bool = False
    remover_raciocinio: bool = False


# ---------------------------------------------------------------------------
# Funcoes auxiliares (puras)
# ---------------------------------------------------------------------------
def _inteiro(valor: Any) -> int:
    try:
        return int(valor or 0)
    except (TypeError, ValueError):
        return 0


def estimar_custo_usd(input_tokens: int, output_tokens: int, cache_read_tokens: int = 0,
                      cache_creation_tokens: int = 0) -> float:
    """
    Custo estimado (USD) de UMA chamada a API com os precos de `config.py`.
    `input_tokens` nao inclui os tokens de cache (como no `usage` da API). Se o prompt
    da chamada passar de LIMITE_TOKENS_PROMPT_LONGO, usa a tabela de prompt longo.
    """
    prompt_total = input_tokens + cache_read_tokens + cache_creation_tokens
    if prompt_total > config.LIMITE_TOKENS_PROMPT_LONGO:
        preco_entrada, preco_saida = config.PRECO_ENTRADA_LONGO_USD_MTOK, config.PRECO_SAIDA_LONGO_USD_MTOK
    else:
        preco_entrada, preco_saida = config.PRECO_ENTRADA_USD_MTOK, config.PRECO_SAIDA_USD_MTOK
    custo = (
        input_tokens * preco_entrada
        + cache_read_tokens * preco_entrada * config.FATOR_CACHE_LEITURA
        + cache_creation_tokens * preco_entrada * config.FATOR_CACHE_ESCRITA
        + output_tokens * preco_saida
    )
    return custo / 1_000_000


def serializar_bloco(bloco: Any) -> dict:
    """
    Converte um bloco de conteudo da API em dict JSON, SEM alterar nada
    (inclui `thinking` com `signature`, mesmo com texto vazio).
    """
    if isinstance(bloco, dict):
        return copy.deepcopy(bloco)
    to_dict = getattr(bloco, "to_dict", None)
    if callable(to_dict):
        return to_dict(mode="json")
    model_dump = getattr(bloco, "model_dump", None)
    if callable(model_dump):
        return model_dump(mode="json", exclude_unset=True, by_alias=True)
    raise TypeError(f"Bloco de conteudo nao serializavel: {type(bloco).__name__}")


def serializar_conteudo(conteudo: Any) -> list[dict] | str:
    """Serializa `response.content` (lista de blocos) para gravar e reenviar."""
    if isinstance(conteudo, str):
        return conteudo
    return [serializar_bloco(bloco) for bloco in (conteudo or [])]


def extrair_texto_blocos(conteudo: list[dict] | str) -> str:
    """Concatena os blocos de texto (ignora thinking/tool_use)."""
    if isinstance(conteudo, str):
        return conteudo.strip()
    partes = [str(b.get("text") or "") for b in conteudo if isinstance(b, dict) and b.get("type") == "text"]
    return SEPARADOR_TEXTO.join(p.strip() for p in partes if p.strip())


def _remover_raciocinio(mensagens: list[dict]) -> list[dict]:
    """
    Copia das mensagens sem blocos thinking/redacted_thinking (recuperacao quando a API
    recusa o raciocinio preservado). Mensagens que ficariam vazias sao omitidas.
    So altera o que e ENVIADO nesta pergunta; o historico gravado continua intacto.
    """
    resultado: list[dict] = []
    for mensagem in mensagens:
        conteudo = mensagem.get("content")
        if isinstance(conteudo, list):
            conteudo = [b for b in conteudo if not (isinstance(b, dict) and b.get("type") in _TIPOS_RACIOCINIO)]
            if not conteudo:
                continue
        resultado.append({"role": mensagem.get("role"), "content": conteudo})
    return resultado


def _tem_raciocinio(mensagens: list[dict]) -> bool:
    return any(
        isinstance(b, dict) and b.get("type") in _TIPOS_RACIOCINIO
        for m in mensagens
        if isinstance(m.get("content"), list)
        for b in m["content"]
    )


def _tool_uses_sem_resultado(historico_api: list[dict]) -> list[str]:
    """Ids dos tool_use da ultima mensagem do historico, se ela for do assistente (turno interrompido)."""
    if not historico_api:
        return []
    ultima = historico_api[-1]
    conteudo = ultima.get("content")
    if ultima.get("role") != "assistant" or not isinstance(conteudo, list):
        return []
    return [str(b.get("id")) for b in conteudo if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("id")]


def _titulo_da_pergunta(pergunta: str) -> str:
    titulo = " ".join(pergunta.split())[: config.TAMANHO_TITULO_CONVERSA].strip()
    return titulo or "Nova conversa"


def _erro_raciocinio_invalido(exc: Exception) -> bool:
    """400 do "preserved thinking" (assinatura do bloco thinking nao confere com a conversa)."""
    if anthropic is None or not isinstance(exc, anthropic.BadRequestError):
        return False
    texto = str(exc).lower()
    return "signature" in texto or "thinking" in texto


def _traduzir_erro_api(exc: Exception) -> ErroDeNegocio | None:
    """Erros do SDK em cadeia (do mais especifico ao mais geral) -> ErroDeNegocio; None se nao for do SDK."""
    if anthropic is None:
        return None
    if isinstance(exc, anthropic.RateLimitError):
        logger.warning("Chatbot: limite de requisicoes da API atingido: %s", exc)
        return ErroDeNegocio(
            code="CHATBOT_LIMITE_REQUISICOES",
            message="Muitas perguntas ao mesmo tempo. Aguarde alguns segundos e tente de novo.",
            status=429,
        )
    if isinstance(exc, anthropic.APIStatusError):
        logger.error("Chatbot: erro da API Anthropic (status %s): %s", exc.status_code, exc)
        if exc.status_code in (401, 403):
            return ErroDeNegocio(
                code="CHATBOT_INDISPONIVEL",
                message="O chatbot esta indisponivel: a chave da API foi recusada.",
                status=503,
            )
        if exc.status_code in (500, 503, 529):
            return ErroDeNegocio(
                code="CHATBOT_INDISPONIVEL",
                message="O servico do assistente esta sobrecarregado ou indisponivel. Tente novamente em instantes.",
                status=503,
            )
        return ErroDeNegocio(
            code="CHATBOT_ERRO_API",
            message=f"O assistente nao conseguiu responder (erro {exc.status_code} na API).",
            status=502,
        )
    if isinstance(exc, anthropic.APIConnectionError):
        logger.error("Chatbot: falha de conexao com a API Anthropic: %s", exc)
        return ErroDeNegocio(
            code="CHATBOT_SEM_CONEXAO",
            message="Nao foi possivel conectar ao servico do assistente. Tente novamente em instantes.",
            status=503,
        )
    return None


# ---------------------------------------------------------------------------
# Servico
# ---------------------------------------------------------------------------
class ChatbotService:
    """Orquestra a conversa com o Claude, as ferramentas somente leitura e o historico no servidor."""

    def __init__(self, cliente: Any = None) -> None:
        # `cliente` permite injetar um cliente (ex.: simulado em testes); sem ele, usa o SDK.
        self._cliente_injetado: Any = cliente
        self._cliente: Any = None
        self._chave_do_cliente: str | None = None

    # ------------------------------------------------------------------
    # Cliente da API
    # ------------------------------------------------------------------
    def definir_cliente(self, cliente: Any) -> None:
        """Usa este cliente em vez de criar um do SDK (testes e avaliacoes). None volta ao padrao."""
        self._cliente_injetado = cliente

    def _obter_cliente(self) -> Any:
        """Cria (ou reaproveita) o cliente da Anthropic; 503 se nao configurado."""
        if self._cliente_injetado is not None:
            return self._cliente_injetado
        if anthropic is None:
            raise ErroDeNegocio(
                code="CHATBOT_INDISPONIVEL",
                message="O chatbot nao esta disponivel: o pacote 'anthropic' nao esta instalado.",
                status=503,
            )
        chave = config.obter_chave_api()
        if chave is None:
            raise ErroDeNegocio(
                code="CHATBOT_INDISPONIVEL",
                message="O chatbot nao esta configurado: defina a variavel ANTHROPIC_API_KEY.",
                status=503,
            )
        if self._cliente is None or chave != self._chave_do_cliente:
            self._cliente = anthropic.Anthropic(
                api_key=chave,
                timeout=config.TIMEOUT_SEGUNDOS,
                max_retries=config.MAX_TENTATIVAS,
            )
            self._chave_do_cliente = chave
        return self._cliente

    # ------------------------------------------------------------------
    # Montagem das mensagens
    # ------------------------------------------------------------------
    @staticmethod
    def _converter_historico(historico: list, mensagem: str | None = None) -> list[dict]:
        """
        Historico de texto da v1: converte [{papel, texto}] (funcionario/assistente) em
        mensagens user/assistant, juntando mensagens seguidas do mesmo papel e descartando
        o que vem antes da primeira mensagem do funcionario. Se `mensagem` vier, ela e
        anexada ao final (compatibilidade com a v1).
        """
        mensagens: list[dict] = []
        for item in (historico or [])[-MAX_MENSAGENS_HISTORICO:]:
            if isinstance(item, dict):
                papel, texto = item.get("papel"), item.get("texto")
            else:  # modelo Pydantic ou objeto equivalente
                papel, texto = getattr(item, "papel", None), getattr(item, "texto", None)
            role = _PAPEIS.get(str(papel or "").strip().lower())
            texto = str(texto or "").strip()
            if role is None or not texto:
                continue
            if not mensagens and role != "user":
                continue  # a conversa precisa comecar com o usuario
            if mensagens and mensagens[-1]["role"] == role:
                mensagens[-1]["content"] += "\n\n" + texto
            else:
                mensagens.append({"role": role, "content": texto})

        if mensagem is not None:
            pergunta = mensagem.strip()
            if mensagens and mensagens[-1]["role"] == "user":
                mensagens[-1]["content"] += "\n\n" + pergunta
            else:
                mensagens.append({"role": "user", "content": pergunta})
        return mensagens

    @staticmethod
    def _montar_system() -> list[dict]:
        """Prompt de sistema fixo (cacheado) e identico em toda a conversa."""
        return [{"type": "text", "text": PROMPT_SISTEMA, "cache_control": {"type": "ephemeral"}}]

    @staticmethod
    def _montar_conteudo_usuario(ctx: ContextoPergunta) -> str | list[dict]:
        """
        Conteudo da nova pergunta: linha de contexto (data + funcionario) + pergunta.
        Se o turno anterior ficou com tool_use sem resultado (resposta interrompida), os
        tool_result de erro vao antes do texto, para o historico continuar valido.
        """
        texto = montar_mensagem_usuario(ctx.pergunta, ctx.funcionario, ctx.hoje)
        pendentes = _tool_uses_sem_resultado(ctx.historico_api)
        if not pendentes:
            return texto
        blocos: list[dict] = [
            {"type": "tool_result", "tool_use_id": id_, "content": MENSAGEM_FERRAMENTA_NAO_EXECUTADA, "is_error": True}
            for id_ in pendentes
        ]
        blocos.append({"type": "text", "text": texto})
        return blocos

    @staticmethod
    def _extrair_texto(resposta: Any) -> str:
        """Concatena os blocos de texto de uma resposta do SDK (ignora thinking/tool_use)."""
        partes = [
            getattr(bloco, "text", "")
            for bloco in (getattr(resposta, "content", None) or [])
            if getattr(bloco, "type", None) == "text"
        ]
        return SEPARADOR_TEXTO.join(p.strip() for p in partes if p and p.strip())

    # ------------------------------------------------------------------
    # Preparacao (validacoes antes de chamar a API)
    # ------------------------------------------------------------------
    def preparar(
        self,
        mensagem: str,
        funcionario: dict,
        conversa_id: str | None = None,
        historico: list | None = None,
        persistir: bool = True,
    ) -> ContextoPergunta:
        """
        Valida o cliente da API e carrega/cria a conversa. Levanta ErroDeNegocio
        (503 sem chave, 404 conversa de outro funcionario ou inexistente, 409 conversa longa)
        ANTES de qualquer chamada a API, para a rota de stream responder com o status certo.
        """
        cliente = self._obter_cliente()
        pergunta = (mensagem or "").strip()
        funcionario_id = int(funcionario.get("id"))

        if conversa_id:
            conversa = self._carregar_conversa(str(conversa_id), funcionario_id)
            mensagens = sorted(conversa.get("mensagens") or [], key=lambda m: m.get("ordem", 0))
            historico_api = [{"role": m.get("papel"), "content": m.get("conteudo")} for m in mensagens]
            if len(historico_api) >= config.MAX_MENSAGENS_CONVERSA:
                raise ErroDeNegocio(
                    code="CONVERSA_MUITO_LONGA",
                    message="Esta conversa atingiu o tamanho maximo. Inicie uma nova conversa para continuar.",
                    status=409,
                )
            return ContextoPergunta(
                cliente=cliente, funcionario=funcionario, pergunta=pergunta,
                conversa_id=str(conversa["id"]), historico_api=historico_api, persistir=persistir,
            )

        # Sem conversa_id: historico de texto da v1 (se houver) + conversa nova no servidor.
        historico_api = self._converter_historico(historico or [])
        pendentes = [
            {"papel": m["role"], "conteudo": m["content"], "texto": m["content"]} for m in historico_api
        ]
        novo_id = self._criar_conversa(funcionario_id, pergunta) if persistir else None
        return ContextoPergunta(
            cliente=cliente, funcionario=funcionario, pergunta=pergunta, conversa_id=novo_id,
            historico_api=historico_api, pendentes_gravacao=pendentes, persistir=persistir,
        )

    @staticmethod
    def _carregar_conversa(conversa_id: str, funcionario_id: int) -> dict:
        try:
            conversa = consultas.obter_conversa(conversa_id, funcionario_id)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Chatbot: nao foi possivel carregar a conversa %s.", conversa_id)
            raise ErroDeNegocio(
                code="CHATBOT_HISTORICO_INDISPONIVEL",
                message="Nao foi possivel carregar o historico da conversa. Tente novamente.",
                status=503,
            ) from exc
        if not conversa:
            raise ErroDeNegocio(code="CONVERSA_NAO_ENCONTRADA", message="Conversa nao encontrada.", status=404)
        return conversa

    @staticmethod
    def _criar_conversa(funcionario_id: int, pergunta: str) -> str | None:
        """Cria a conversa no servidor; se falhar, o chat segue sem guardar o historico (com log)."""
        try:
            conversa = consultas.criar_conversa(funcionario_id, _titulo_da_pergunta(pergunta))
            return str(conversa["id"])
        except Exception:  # noqa: BLE001
            logger.exception("Chatbot: nao foi possivel criar a conversa; seguindo sem historico no servidor.")
            return None

    # ------------------------------------------------------------------
    # Chamada a API (uma volta)
    # ------------------------------------------------------------------
    def _parametros(self, system: list[dict], mensagens: list[dict], estado: _EstadoTurno) -> dict:
        enviadas = _remover_raciocinio(mensagens) if estado.remover_raciocinio else mensagens
        return {
            "model": config.CHATBOT_MODELO,
            "max_tokens": config.MAX_TOKENS,
            "system": system,
            "tools": TOOLS,
            "messages": enviadas,
            "output_config": {"effort": config.CHATBOT_ESFORCO},
            # Cache automatico do historico (prefixo cresce a cada volta); o system tem o seu proprio ponto.
            "cache_control": {"type": "ephemeral"},
        }

    def _chamar_modelo(self, cliente: Any, system: list[dict], mensagens: list[dict],
                       estado: _EstadoTurno | None = None) -> Any:
        """Uma chamada a messages.create (modo sincrono), com os erros do SDK traduzidos para ErroDeNegocio."""
        estado = estado or _EstadoTurno()
        while True:
            try:
                return cliente.messages.create(**self._parametros(system, mensagens, estado))
            except Exception as exc:  # noqa: BLE001
                if not estado.remover_raciocinio and _erro_raciocinio_invalido(exc) and _tem_raciocinio(mensagens):
                    logger.warning("Chatbot: raciocinio preservado recusado pela API; reenviando sem os blocos thinking.")
                    estado.remover_raciocinio = True
                    continue
                erro = _traduzir_erro_api(exc)
                if erro is not None:
                    raise erro from exc
                raise

    def _rodada_stream(self, cliente: Any, system: list[dict], mensagens: list[dict],
                       estado: _EstadoTurno) -> Generator[dict, None, Any]:
        """
        Uma volta com `client.messages.stream(...)`: emite eventos de texto/ferramenta
        enquanto o modelo gera e devolve a mensagem final (`get_final_message()`).
        """
        repeticoes_json = 0
        while True:
            try:
                with cliente.messages.stream(**self._parametros(system, mensagens, estado)) as stream:
                    for evento in stream:
                        tipo = getattr(evento, "type", None)
                        if tipo == "content_block_start":
                            bloco = getattr(evento, "content_block", None)
                            tipo_bloco = getattr(bloco, "type", None)
                            if tipo_bloco == "tool_use":
                                yield {"tipo": "ferramenta", "nome": getattr(bloco, "name", "")}
                            elif tipo_bloco == "text" and estado.ja_emitiu_texto:
                                yield {"tipo": "texto", "delta": SEPARADOR_TEXTO}
                        elif tipo == "content_block_delta":
                            delta = getattr(evento, "delta", None)
                            if getattr(delta, "type", None) == "text_delta":
                                pedaco = getattr(delta, "text", "") or ""
                                if pedaco:
                                    estado.ja_emitiu_texto = True
                                    yield {"tipo": "texto", "delta": pedaco}
                    return stream.get_final_message()
            except ErroDeNegocio:
                raise
            except Exception as exc:  # noqa: BLE001
                if not estado.remover_raciocinio and _erro_raciocinio_invalido(exc) and _tem_raciocinio(mensagens):
                    logger.warning("Chatbot: raciocinio preservado recusado pela API; reenviando sem os blocos thinking.")
                    estado.remover_raciocinio = True
                    continue
                erro = _traduzir_erro_api(exc)
                if erro is not None:
                    raise erro from exc
                if isinstance(exc, ValueError) and repeticoes_json < config.MAX_REPETICOES_JSON_INVALIDO:
                    # JSON da entrada de uma ferramenta que o SDK nao conseguiu ler (eager_input_streaming):
                    # nao ha tool_use completo para responder, entao a volta e repetida (limite pequeno).
                    repeticoes_json += 1
                    logger.warning("Chatbot: JSON invalido na entrada de ferramenta (%s); repetindo a volta.", exc)
                    continue
                raise

    def _rodada(self, cliente: Any, system: list[dict], mensagens: list[dict], estado: _EstadoTurno,
                ao_vivo: bool) -> Generator[dict, None, Any]:
        if ao_vivo:
            return (yield from self._rodada_stream(cliente, system, mensagens, estado))
        return self._chamar_modelo(cliente, system, mensagens, estado)

    # ------------------------------------------------------------------
    # Ferramentas de uma volta
    # ------------------------------------------------------------------
    @staticmethod
    def _executar_ferramentas(blocos: list[dict], ferramentas_usadas: list[str]) -> list[dict]:
        """Executa TODOS os tool_use da volta (com validacao da entrada) e devolve os tool_result."""
        resultados: list[dict] = []
        for bloco in blocos:
            nome = str(bloco.get("name") or "")
            conteudo, erro = executar_ferramenta(nome, bloco.get("input"))
            if nome and nome not in ferramentas_usadas:
                ferramentas_usadas.append(nome)
            resultados.append(
                {"type": "tool_result", "tool_use_id": bloco.get("id"), "content": conteudo, "is_error": erro}
            )
        return resultados

    # ------------------------------------------------------------------
    # Fluxo principal (gerador de eventos)
    # ------------------------------------------------------------------
    def executar(self, ctx: ContextoPergunta, ao_vivo: bool = False) -> Iterator[dict]:
        """
        Responde a pergunta e emite os eventos:
        {"tipo": "inicio"}, {"tipo": "texto"} (so no stream), {"tipo": "ferramenta"} (so no stream)
        e, por ultimo, {"tipo": "fim", resposta, ferramentas_usadas, modelo, conversa_id, uso}.
        Erros saem como ErroDeNegocio (a rota de stream os converte no evento "erro").
        """
        inicio = time.monotonic()
        yield {"tipo": "inicio", "conversa_id": ctx.conversa_id}

        system = self._montar_system()
        conteudo_usuario = self._montar_conteudo_usuario(ctx)
        mensagens: list[dict] = list(ctx.historico_api) + [{"role": "user", "content": conteudo_usuario}]
        novas: list[dict] = [{"papel": "user", "conteudo": conteudo_usuario, "texto": ctx.pergunta}]

        estado = _EstadoTurno()
        uso = UsoAcumulado()
        ferramentas_usadas: list[str] = []
        textos: list[str] = []
        texto_final: str | None = None

        for _volta in range(config.MAX_VOLTAS):
            resposta = yield from self._rodada(ctx.cliente, system, mensagens, estado, ao_vivo)
            uso.somar(getattr(resposta, "usage", None))
            motivo = getattr(resposta, "stop_reason", None)
            conteudo = serializar_conteudo(getattr(resposta, "content", None))
            texto_volta = extrair_texto_blocos(conteudo)
            if texto_volta:
                textos.append(texto_volta)

            mensagens.append({"role": "assistant", "content": conteudo})
            novas.append({"papel": "assistant", "conteudo": conteudo, "texto": ""})
            tool_uses = [b for b in conteudo if isinstance(b, dict) and b.get("type") == "tool_use"]

            if motivo == "tool_use":
                if not tool_uses:  # tool_use sem blocos: evita loop vazio
                    texto_final = SEPARADOR_TEXTO.join(textos) or MENSAGEM_SEM_TEXTO
                    novas[-1]["texto"] = texto_final
                    break
                resultados = self._executar_ferramentas(tool_uses, ferramentas_usadas)
                mensagens.append({"role": "user", "content": resultados})
                novas.append({"papel": "user", "conteudo": resultados, "texto": ""})
                continue

            if motivo == "pause_turn":
                # Turno pausado pelo servidor: reenvia para o modelo continuar de onde parou.
                continue

            if motivo == "max_tokens":
                texto_final = (SEPARADOR_TEXTO.join(textos) or "Resposta muito longa.") + AVISO_MAX_TOKENS
                if ao_vivo:
                    yield {"tipo": "texto", "delta": AVISO_MAX_TOKENS}
            elif motivo == "refusal":
                texto_final = MENSAGEM_RECUSA
            else:  # end_turn, stop_sequence ou outro motivo final
                texto_final = SEPARADOR_TEXTO.join(textos) or MENSAGEM_SEM_TEXTO

            # Se a resposta foi cortada (max_tokens/recusa) no meio de um tool_use, a entrada pode estar
            # truncada: a ferramenta NAO e executada. O tool_result de erro vai no inicio da proxima
            # pergunta (`_montar_conteudo_usuario`), mantendo o historico valido e so de acrescimo.
            novas[-1]["texto"] = texto_final
            break

        if texto_final is None:
            logger.warning("Chatbot: limite de %s voltas de tool use atingido.", config.MAX_VOLTAS)
            texto_final = MENSAGEM_LIMITE_VOLTAS
            # Texto visivel na ultima mensagem do assistente (a seguinte e a de tool_result).
            for mensagem in reversed(novas):
                if mensagem["papel"] == "assistant":
                    mensagem["texto"] = texto_final
                    break

        duracao_ms = int((time.monotonic() - inicio) * 1000)
        uso_dict = uso.como_dict()
        if ctx.persistir:
            self._gravar_turno(ctx, novas)
            self._registrar(ctx.funcionario, ctx.pergunta, texto_final, ferramentas_usadas,
                            conversa_id=ctx.conversa_id, uso=uso_dict, duracao_ms=duracao_ms)

        yield {
            "tipo": "fim",
            "resposta": texto_final,
            "ferramentas_usadas": ferramentas_usadas,
            "modelo": config.CHATBOT_MODELO,
            "conversa_id": ctx.conversa_id,
            "uso": uso_dict,
            "duracao_ms": duracao_ms,
        }

    def responder(self, mensagem: str, historico: list | None, funcionario: dict,
                  conversa_id: str | None = None) -> dict:
        """
        Modo sincrono. Devolve {"resposta", "ferramentas_usadas", "modelo", "conversa_id", "uso"}.
        Com `conversa_id`, o historico vem do servidor e `historico` e ignorado.
        """
        ctx = self.preparar(mensagem, funcionario, conversa_id=conversa_id, historico=historico)
        return self.responder_contexto(ctx)

    def responder_contexto(self, ctx: ContextoPergunta) -> dict:
        """Executa uma pergunta ja preparada no modo sincrono e devolve o conteudo do evento "fim"."""
        final: dict = {}
        for evento in self.executar(ctx, ao_vivo=False):
            if evento.get("tipo") == "fim":
                final = evento
        return {
            "resposta": final.get("resposta", MENSAGEM_SEM_TEXTO),
            "ferramentas_usadas": final.get("ferramentas_usadas", []),
            "modelo": final.get("modelo", config.CHATBOT_MODELO),
            "conversa_id": final.get("conversa_id"),
            "uso": final.get("uso", UsoAcumulado().como_dict()),
        }

    # ------------------------------------------------------------------
    # Persistencia
    # ------------------------------------------------------------------
    @staticmethod
    def _gravar_turno(ctx: ContextoPergunta, novas: list[dict]) -> None:
        """Acrescenta as mensagens do turno (e o historico da v1, se houver) a conversa. Nunca altera as antigas."""
        if not ctx.conversa_id:
            return
        try:
            consultas.adicionar_mensagens(ctx.conversa_id, list(ctx.pendentes_gravacao) + list(novas))
            ctx.pendentes_gravacao = []
        except Exception:  # noqa: BLE001
            logger.exception("Chatbot: nao foi possivel gravar as mensagens da conversa %s.", ctx.conversa_id)

    @staticmethod
    def _registrar(funcionario: dict, pergunta: str, resposta: str, ferramentas_usadas: list[str], *,
                   conversa_id: str | None = None, uso: dict | None = None, duracao_ms: int | None = None) -> None:
        """Registra a troca para auditoria (LGPD) e uso/custo. Falha no registro nao derruba o chat."""
        argumentos = {
            "funcionario_id": int(funcionario.get("id")),
            "pergunta": pergunta,
            "resposta": resposta,
            "ferramentas_usadas": list(ferramentas_usadas),
        }
        try:
            registrar_chat(**argumentos, conversa_id=conversa_id, modelo=config.CHATBOT_MODELO,
                           uso=uso, duracao_ms=duracao_ms)
        except TypeError:
            # Banco ainda na assinatura da v1: registra ao menos a troca.
            logger.warning("Chatbot: registrar_chat sem os campos de uso; registrando no formato da v1.")
            try:
                registrar_chat(**argumentos)
            except Exception:  # noqa: BLE001
                logger.exception("Chatbot: nao foi possivel registrar a conversa na auditoria.")
        except Exception:  # noqa: BLE001
            logger.exception("Chatbot: nao foi possivel registrar a conversa na auditoria.")

    # ------------------------------------------------------------------
    # Conversas (rotas de leitura)
    # ------------------------------------------------------------------
    @staticmethod
    def listar_conversas(funcionario: dict, limite: int = config.LIMITE_CONVERSAS_LISTADAS) -> list[dict]:
        """Conversas do funcionario logado, mais recentes primeiro."""
        conversas = consultas.listar_conversas(int(funcionario.get("id")), limite=limite) or []
        return [
            {
                "id": c.get("id"),
                "titulo": c.get("titulo"),
                "criado_em": c.get("criado_em"),
                "atualizado_em": c.get("atualizado_em"),
                "total_mensagens": c.get("total_mensagens", 0),
            }
            for c in conversas
        ]

    @staticmethod
    def obter_conversa_visivel(conversa_id: str, funcionario: dict) -> dict:
        """
        Conversa para reabrir na interface: so as mensagens com texto visivel, com papel
        "funcionario"/"assistente". 404 se nao existir ou for de outro funcionario.
        """
        conversa = ChatbotService._carregar_conversa(str(conversa_id), int(funcionario.get("id")))
        mensagens = sorted(conversa.get("mensagens") or [], key=lambda m: m.get("ordem", 0))
        visiveis = [
            {"papel": "funcionario" if m.get("papel") == "user" else "assistente", "texto": m.get("texto")}
            for m in mensagens
            if str(m.get("texto") or "").strip()
        ]
        return {"id": conversa.get("id"), "titulo": conversa.get("titulo"), "mensagens": visiveis}


# Uma unica instancia compartilhada por toda a aplicacao.
chatbot_service = ChatbotService()
