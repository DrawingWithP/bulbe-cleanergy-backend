"""
Camada de Servico, ChatbotService.

Conversa com o Claude (SDK oficial `anthropic`) usando um loop MANUAL de tool use:
1. envia system + tools + historico + pergunta;
2. enquanto stop_reason == "tool_use", executa TODAS as ferramentas pedidas
   e devolve TODOS os tool_result numa unica mensagem "user";
3. termina em "end_turn" (ou trata "max_tokens", "refusal" e "pause_turn").

O historico e sem estado no servidor: a interface reenvia as trocas anteriores.
"""
import logging
from datetime import date
from typing import Any

from app.chatbot import config
from app.chatbot.ferramentas import TOOLS, executar_ferramenta
from app.chatbot.prompts import PROMPT_SISTEMA, montar_contexto_dinamico
from app.database.consultas import registrar_chat
from app.services.usina_service import ErroDeNegocio

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

_PAPEIS: dict[str, str] = {"funcionario": "user", "assistente": "assistant"}


class ChatbotService:
    """Orquestra a conversa com o Claude e as ferramentas somente leitura."""

    def __init__(self) -> None:
        self._cliente: Any = None
        self._chave_do_cliente: str | None = None

    # ------------------------------------------------------------------
    # Cliente da API
    # ------------------------------------------------------------------
    def _obter_cliente(self) -> Any:
        """Cria (ou reaproveita) o cliente da Anthropic; 503 se nao configurado."""
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
    def _converter_historico(historico: list, mensagem: str) -> list[dict]:
        """
        Converte [{papel, texto}] (funcionario/assistente) em mensagens user/assistant,
        juntando mensagens seguidas do mesmo papel, descartando o que vem antes da
        primeira mensagem do funcionario e terminando com a pergunta atual (user).
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

        pergunta = mensagem.strip()
        if mensagens and mensagens[-1]["role"] == "user":
            mensagens[-1]["content"] += "\n\n" + pergunta
        else:
            mensagens.append({"role": "user", "content": pergunta})
        return mensagens

    @staticmethod
    def _montar_system(funcionario: dict) -> list[dict]:
        """Bloco fixo (cacheado) + bloco dinamico (fora do cache)."""
        return [
            {"type": "text", "text": PROMPT_SISTEMA, "cache_control": {"type": "ephemeral"}},
            {"type": "text", "text": montar_contexto_dinamico(funcionario, date.today())},
        ]

    @staticmethod
    def _extrair_texto(resposta: Any) -> str:
        """Concatena os blocos de texto da resposta (ignora thinking/tool_use)."""
        partes = [
            getattr(bloco, "text", "")
            for bloco in (getattr(resposta, "content", None) or [])
            if getattr(bloco, "type", None) == "text"
        ]
        return "\n\n".join(p.strip() for p in partes if p and p.strip())

    # ------------------------------------------------------------------
    # Chamada a API
    # ------------------------------------------------------------------
    def _chamar_modelo(self, cliente: Any, system: list[dict], mensagens: list[dict]) -> Any:
        """Uma chamada a messages.create, com os erros do SDK traduzidos para ErroDeNegocio."""
        try:
            return cliente.messages.create(
                model=config.CHATBOT_MODELO,
                max_tokens=config.MAX_TOKENS,
                system=system,
                tools=TOOLS,
                messages=mensagens,
                output_config={"effort": config.CHATBOT_ESFORCO},
            )
        except anthropic.RateLimitError as exc:
            logger.warning("Chatbot: limite de requisicoes da API atingido: %s", exc)
            raise ErroDeNegocio(
                code="CHATBOT_LIMITE_REQUISICOES",
                message="Muitas perguntas ao mesmo tempo. Aguarde alguns segundos e tente de novo.",
                status=429,
            ) from exc
        except anthropic.APIStatusError as exc:
            logger.error("Chatbot: erro da API Anthropic (status %s): %s", exc.status_code, exc)
            if exc.status_code in (401, 403):
                raise ErroDeNegocio(
                    code="CHATBOT_INDISPONIVEL",
                    message="O chatbot esta indisponivel: a chave da API foi recusada.",
                    status=503,
                ) from exc
            if exc.status_code in (500, 503, 529):
                raise ErroDeNegocio(
                    code="CHATBOT_INDISPONIVEL",
                    message="O servico do assistente esta sobrecarregado ou indisponivel. Tente novamente em instantes.",
                    status=503,
                ) from exc
            raise ErroDeNegocio(
                code="CHATBOT_ERRO_API",
                message=f"O assistente nao conseguiu responder (erro {exc.status_code} na API).",
                status=502,
            ) from exc
        except anthropic.APIConnectionError as exc:
            logger.error("Chatbot: falha de conexao com a API Anthropic: %s", exc)
            raise ErroDeNegocio(
                code="CHATBOT_SEM_CONEXAO",
                message="Nao foi possivel conectar ao servico do assistente. Tente novamente em instantes.",
                status=503,
            ) from exc

    # ------------------------------------------------------------------
    # Fluxo principal
    # ------------------------------------------------------------------
    def responder(self, mensagem: str, historico: list, funcionario: dict) -> dict:
        """
        Responde a pergunta do funcionario usando o Claude + ferramentas.

        Devolve {"resposta": str, "ferramentas_usadas": [str], "modelo": str}.
        """
        cliente = self._obter_cliente()
        system = self._montar_system(funcionario)
        mensagens = self._converter_historico(historico, mensagem)
        ferramentas_usadas: list[str] = []
        texto_final: str | None = None
        ultimo_texto = ""

        for _volta in range(config.MAX_VOLTAS):
            resposta = self._chamar_modelo(cliente, system, mensagens)
            motivo = getattr(resposta, "stop_reason", None)
            ultimo_texto = self._extrair_texto(resposta) or ultimo_texto

            if motivo == "tool_use":
                mensagens.append({"role": "assistant", "content": resposta.content})
                resultados: list[dict] = []
                for bloco in resposta.content:
                    if getattr(bloco, "type", None) != "tool_use":
                        continue
                    conteudo, erro = executar_ferramenta(bloco.name, bloco.input)
                    if bloco.name not in ferramentas_usadas:
                        ferramentas_usadas.append(bloco.name)
                    resultados.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": bloco.id,
                            "content": conteudo,
                            "is_error": erro,
                        }
                    )
                if not resultados:  # tool_use sem blocos: evita loop vazio
                    texto_final = ultimo_texto or MENSAGEM_SEM_TEXTO
                    break
                mensagens.append({"role": "user", "content": resultados})
                continue

            if motivo == "pause_turn":
                # Turno pausado pelo servidor: reenvia para o modelo continuar de onde parou.
                mensagens.append({"role": "assistant", "content": resposta.content})
                continue

            texto = self._extrair_texto(resposta)
            if motivo == "max_tokens":
                texto_final = (texto or ultimo_texto or "Resposta muito longa.") + AVISO_MAX_TOKENS
            elif motivo == "refusal":
                texto_final = MENSAGEM_RECUSA
            else:  # end_turn, stop_sequence ou outro motivo final
                texto_final = texto or MENSAGEM_SEM_TEXTO
            break

        if texto_final is None:
            logger.warning("Chatbot: limite de %s voltas de tool use atingido.", config.MAX_VOLTAS)
            texto_final = MENSAGEM_LIMITE_VOLTAS

        self._registrar(funcionario, mensagem, texto_final, ferramentas_usadas)
        return {
            "resposta": texto_final,
            "ferramentas_usadas": ferramentas_usadas,
            "modelo": config.CHATBOT_MODELO,
        }

    @staticmethod
    def _registrar(funcionario: dict, pergunta: str, resposta: str, ferramentas_usadas: list[str]) -> None:
        """Registra a troca para auditoria (LGPD). Falha no registro nao derruba o chat."""
        try:
            registrar_chat(
                funcionario_id=int(funcionario.get("id")),
                pergunta=pergunta,
                resposta=resposta,
                ferramentas_usadas=list(ferramentas_usadas),
            )
        except Exception:  # noqa: BLE001
            logger.exception("Chatbot: nao foi possivel registrar a conversa na auditoria.")


# Uma unica instancia compartilhada por toda a aplicacao.
chatbot_service = ChatbotService()
