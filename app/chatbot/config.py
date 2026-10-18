"""
Camada de Configuracao, Chatbot.

Le as variaveis de ambiente usadas pelo chatbot. Se o pacote `python-dotenv`
estiver instalado, carrega o arquivo `.env` (procurando a partir desta pasta
ate a raiz do projeto) sem sobrescrever variaveis ja definidas. Se nao estiver
instalado, segue apenas com as variaveis do sistema, sem quebrar.
"""
import os

try:
    from dotenv import load_dotenv

    load_dotenv(override=False)
except ImportError:  # python-dotenv e opcional
    pass

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


def obter_chave_api() -> str | None:
    """
    Devolve a ANTHROPIC_API_KEY atual (lida a cada chamada, para permitir
    configurar a chave sem reiniciar o processo) ou None se estiver vazia.
    """
    chave = os.getenv("ANTHROPIC_API_KEY", "").strip()
    return chave or None
