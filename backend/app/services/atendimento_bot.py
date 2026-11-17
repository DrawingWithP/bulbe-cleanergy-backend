"""
Robo de respostas automaticas do atendimento pelo app.

Regras simples e previsiveis (sem IA): o cliente escolhe um topico pelos
botoes ou escreve uma frase; o robo identifica o topico por palavras-chave e
responde com os dados do proprio cliente (etapa da ativacao, Clube,
indicacoes). Depois de responder, oferece "Resolveu", "Outra duvida" ou
"Falar com um atendente".
"""

import unicodedata
from dataclasses import dataclass
from datetime import date


OPCAO_RESOLVEU = "Resolveu, obrigado!"
OPCAO_OUTRA = "Tenho outra dúvida"
OPCAO_ATENDENTE = "Falar com um atendente"

TOPICOS = {
    "prazo": "Prazo da minha conexão",
    "fatura": "Minha conta de luz",
    "clube": "Clube Bulbe e cupons",
    "indicacao": "Indique e ganhe",
    "endereco": "Mudança de endereço",
}

PALAVRAS = {
    "atendente": ("atendente", "humano", "pessoa", "falar com alguem", "falar com um"),
    "resolveu": ("resolveu", "obrigad", "valeu", "era isso", "pode encerrar"),
    "outra": ("outra duvida", "outra pergunta", "menu", "voltar"),
    "prazo": ("prazo", "conex", "ativa", "cemig", "etapa", "quando", "demora", "liberad"),
    "fatura": ("fatura", "conta", "boleto", "pagar", "pagamento", "desconto", "valor", "segunda via", "2a via"),
    "clube": ("clube", "carta", "cupom", "cupons", "sequencia", "premio", "bonus"),
    "indicacao": ("indic", "amigo", "indique"),
    "endereco": ("endereco", "mudanca", "mudar", "mudei", "casa nova"),
}

OPCOES_MENU = list(TOPICOS.values()) + [OPCAO_ATENDENTE]
OPCOES_DEPOIS = [OPCAO_RESOLVEU, OPCAO_OUTRA, OPCAO_ATENDENTE]


@dataclass
class RespostaBot:
    texto: str
    opcoes: list[str] | None
    acao: str | None = None  # "atendente" | "resolvido" | None


def _normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return " ".join(sem_acento.lower().split())


def identificar(texto: str) -> str | None:
    """Topico (ou acao) da mensagem do cliente; None se nao entender."""
    normal = _normalizar(texto)
    for chave, rotulo in TOPICOS.items():
        if normal == _normalizar(rotulo):
            return chave
    for chave in ("atendente", "resolveu", "outra"):
        if any(palavra in normal for palavra in PALAVRAS[chave]):
            return chave
    for chave in TOPICOS:
        if any(palavra in normal for palavra in PALAVRAS[chave]):
            return chave
    return None


def boas_vindas(primeiro_nome: str) -> RespostaBot:
    return RespostaBot(
        f"Oi, {primeiro_nome}! Eu sou a assistente da Bulbe. Sobre o que você quer falar? "
        "Escolha uma opção ou escreva sua dúvida.",
        OPCOES_MENU,
    )


def _data_br(iso: str | None) -> str:
    try:
        return date.fromisoformat((iso or "")[:10]).strftime("%d/%m/%Y")
    except ValueError:
        return "em breve"


def responder(texto: str, dados: dict) -> RespostaBot:
    """
    Resposta do robo. `dados` traz o que o servico conseguiu ler do cliente:
    ativacao (dict), clube (dict), indicacoes (list).
    """
    topico = identificar(texto)

    if topico == "atendente":
        return RespostaBot(
            "Certo! Já chamei um atendente. Fica tranquilo(a): você continua nesta conversa e a resposta "
            "aparece aqui mesmo.",
            None,
            acao="atendente",
        )
    if topico == "resolveu":
        return RespostaBot("Que bom que ajudei! Se precisar, é só abrir uma nova conversa. ☀️", None,
                           acao="resolvido")
    if topico == "outra":
        return RespostaBot("Claro! Sobre o que mais você quer saber?", OPCOES_MENU)

    if topico == "prazo":
        ativacao = dados.get("ativacao")
        if ativacao:
            texto_resposta = (
                f"Sua conexão está na etapa {ativacao['etapa_atual']} de {ativacao.get('total_etapas', 5)}: "
                f"{ativacao['titulo']}. {ativacao.get('descricao', '')} "
                f"A previsão para a energia ser liberada é {_data_br(ativacao.get('previsao_conclusao'))}. "
                "O prazo total é de até 90 dias, porque depende da análise da CEMIG."
            )
        else:
            texto_resposta = ("A ativação leva até 90 dias e depende da análise da CEMIG. "
                              "Você acompanha cada etapa na tela Conexão do app.")
        return RespostaBot(" ".join(texto_resposta.split()), OPCOES_DEPOIS)

    if topico == "fatura":
        return RespostaBot(
            "Com a Bulbe você recebe até 15% de desconto na parte da conta em que o desconto incide "
            "(não incide em iluminação pública nem PIS/COFINS). O desconto começa depois que a energia é "
            "liberada. Bônus de indicação e do Clube entram como desconto na fatura seguinte.",
            OPCOES_DEPOIS,
        )

    if topico == "clube":
        clube = dados.get("clube")
        if clube:
            proxima = clube.get("proxima_carta") or {}
            if clube.get("carta_disponivel"):
                quando = "Sua carta da semana já está disponível na tela Vantagens!"
            else:
                quando = f"A próxima carta chega em {proxima.get('dias_restantes', 7)} dia(s)."
            texto_resposta = (
                f"Você está com {clube.get('semanas_sequencia', 0)} de {clube.get('meta_sequencia', 5)} "
                f"semanas seguidas no Clube. {quando} Ao completar 5 semanas, a carta especial vale "
                "R$ 50 de desconto na fatura."
            )
        else:
            texto_resposta = ("No Clube Bulbe você abre uma carta por semana e ganha cupons de parceiros. "
                              "Em 5 semanas seguidas, a carta especial vale R$ 50 na fatura.")
        return RespostaBot(texto_resposta, OPCOES_DEPOIS)

    if topico == "indicacao":
        indicacoes = dados.get("indicacoes") or []
        aderiram = [i for i in indicacoes if i.get("situacao") == "aderiu"]
        texto_resposta = (
            f"Você já indicou {len(indicacoes)} pessoa(s) e {len(aderiram)} virou(aram) cliente. "
            "Cada amigo que virar cliente vale R$ 50 de desconto para você e R$ 50 para ele. "
            "Para indicar, use a tela Indicações do app."
        )
        return RespostaBot(texto_resposta, OPCOES_DEPOIS)

    if topico == "endereco":
        return RespostaBot(
            "Para mudar o endereço da conta, precisamos do número da nova instalação da CEMIG e da data da "
            "mudança. Um atendente cuida disso para você: toque em \"Falar com um atendente\".",
            OPCOES_DEPOIS,
        )

    return RespostaBot(
        "Desculpe, não entendi. Você pode escolher um dos assuntos abaixo ou falar com um atendente.",
        OPCOES_MENU,
    )
