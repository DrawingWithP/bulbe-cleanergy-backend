"""
Camada de Configuracao, Chatbot.

Le as variaveis de ambiente usadas pelo chatbot. Se o pacote `python-dotenv`
estiver instalado, carrega o arquivo `.env` (procurando a partir desta pasta
ate a raiz do projeto) sem sobrescrever variaveis ja definidas. Se nao estiver
instalado, segue apenas com as variaveis do sistema, sem quebrar.
"""
import logging
import os

try:
    from dotenv import load_dotenv

    load_dotenv(override=False)
except ImportError:  # python-dotenv e opcional
    pass

logger = logging.getLogger(__name__)


def _ler_float(nome: str, padrao: float) -> float:
    """Le um numero real do ambiente; valor vazio ou invalido volta ao padrao (com aviso)."""
    bruto = os.getenv(nome, "").strip().replace(",", ".")
    if not bruto:
        return padrao
    try:
        valor = float(bruto)
    except ValueError:
        logger.warning("Variavel %s invalida (%r); usando o padrao %s.", nome, bruto, padrao)
        return padrao
    if valor < 0 or valor != valor:
        logger.warning("Variavel %s negativa ou invalida (%r); usando o padrao %s.", nome, bruto, padrao)
        return padrao
    return valor


def _ler_int(nome: str, padrao: int, minimo: int = 1) -> int:
    """Le um inteiro do ambiente; valor vazio, invalido ou abaixo do minimo volta ao padrao."""
    bruto = os.getenv(nome, "").strip()
    if not bruto:
        return padrao
    try:
        valor = int(bruto)
    except ValueError:
        logger.warning("Variavel %s invalida (%r); usando o padrao %s.", nome, bruto, padrao)
        return padrao
    return valor if valor >= minimo else padrao


# Modelo do Claude usado pelo chatbot.
MODELO_PADRAO: str = "claude-haiku-5-5"
CHATBOT_MODELO: str = os.getenv("CHATBOT_MODELO", MODELO_PADRAO).strip() or MODELO_PADRAO

# Nivel de esforco (output_config.effort). "high" prioriza respostas mais cuidadosas (padrao pedido pelo usuario).
ESFORCO_PADRAO: str = "high"
CHATBOT_ESFORCO: str = (os.getenv("CHATBOT_ESFORCO", ESFORCO_PADRAO).strip().lower() or ESFORCO_PADRAO)

# Limites do loop de tool use.
MAX_TOKENS: int = 8000
MAX_VOLTAS: int = 8

# Tempo maximo (segundos) de cada chamada a API e numero de novas tentativas do SDK.
TIMEOUT_SEGUNDOS: float = float(os.getenv("CHATBOT_TIMEOUT", "60") or 60)
MAX_TENTATIVAS: int = 2

# Quantas vezes uma volta do stream e repetida quando o SDK nao consegue ler o JSON
# da entrada de uma ferramenta (eager_input_streaming).
MAX_REPETICOES_JSON_INVALIDO: int = 2

# Conversas no servidor: limite de mensagens guardadas (da API) por conversa. Acima disso,
# a conversa nao aceita novas perguntas (o historico e so de acrescimo e nao pode ser cortado
# sem invalidar o raciocinio preservado); o funcionario deve abrir uma nova conversa.
MAX_MENSAGENS_CONVERSA: int = _ler_int("CHATBOT_MAX_MENSAGENS_CONVERSA", 200)
# Quantidade padrao de conversas listadas em GET /v1/painel/chat/conversas.
LIMITE_CONVERSAS_LISTADAS: int = 20
# Tamanho maximo do titulo gerado a partir da primeira pergunta.
TAMANHO_TITULO_CONVERSA: int = 60

# ---------------------------------------------------------------------------
# Precos (USD por milhao de tokens) para o custo ESTIMADO de cada pergunta.
# Padrao: Claude Haiku 5.5 com prompt de ate 100 mil tokens (US$ 0,10 entrada / US$ 0,50 saida).
# Leitura de cache = 0,1 x entrada; escrita de cache (5 min) = 1,25 x entrada.
# Acima de LIMITE_TOKENS_PROMPT_LONGO tokens de entrada numa chamada, a Anthropic cobra
# a tabela de prompt longo (Haiku 5.5: US$ 0,50 / US$ 2,50). Ajuste pelo .env se os precos mudarem
# ou se outro modelo for usado.
# ---------------------------------------------------------------------------
PRECO_ENTRADA_USD_MTOK: float = _ler_float("CHATBOT_PRECO_ENTRADA_MTOK", 0.10)
PRECO_SAIDA_USD_MTOK: float = _ler_float("CHATBOT_PRECO_SAIDA_MTOK", 0.50)
FATOR_CACHE_LEITURA: float = _ler_float("CHATBOT_FATOR_CACHE_LEITURA", 0.1)
FATOR_CACHE_ESCRITA: float = _ler_float("CHATBOT_FATOR_CACHE_ESCRITA", 1.25)
LIMITE_TOKENS_PROMPT_LONGO: int = _ler_int("CHATBOT_LIMITE_PROMPT_LONGO", 100_000)
PRECO_ENTRADA_LONGO_USD_MTOK: float = _ler_float("CHATBOT_PRECO_ENTRADA_LONGO_MTOK", 0.50)
PRECO_SAIDA_LONGO_USD_MTOK: float = _ler_float("CHATBOT_PRECO_SAIDA_LONGO_MTOK", 2.50)


def obter_chave_api() -> str | None:
    """
    Devolve a ANTHROPIC_API_KEY atual (lida a cada chamada, para permitir
    configurar a chave sem reiniciar o processo) ou None se estiver vazia.
    """
    chave = os.getenv("ANTHROPIC_API_KEY", "").strip()
    return chave or None
