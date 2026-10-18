"""
Camada de Ferramentas, Chatbot.

Define as ferramentas (tools) que o Claude pode chamar e executa cada uma
delas contra as consultas SOMENTE LEITURA de `app.database.consultas`
(mapeamento 1-para-1, secao 1.6 do contrato).

Uma unica especificacao (`_ESPECIFICACAO`) gera:
- a lista `TOOLS` (JSON Schema enviado a API);
- a validacao/conversao das entradas antes de chamar a consulta.

Antes de devolver o resultado ao modelo, CPF e telefone sao mascarados
recursivamente (LGPD) e o resultado e serializado em JSON.
"""
import json
import logging
import re
from typing import Any

from app.database import consultas

logger = logging.getLogger(__name__)

# Tamanho maximo (em caracteres) do resultado devolvido ao modelo por ferramenta.
LIMITE_CARACTERES_RESULTADO: int = 40000
# Tamanho maximo de qualquer texto recebido como parametro.
LIMITE_CARACTERES_TEXTO: int = 200

# ---------------------------------------------------------------------------
# Valores aceitos (secao 1.3 do contrato)
# ---------------------------------------------------------------------------
STATUS_CLIENTE = ["ativo", "em_ativacao", "cancelado"]
SITUACAO_FATURA = ["paga", "em_aberto", "vencida"]
SITUACAO_CUPOM = ["ativo", "salvo", "usado", "expirado", "descartado"]
STATUS_ATENDIMENTO = ["aberto", "em_andamento", "resolvido"]
SITUACAO_ADESAO = ["rascunho", "enviada", "aprovada", "recusada"]

# ---------------------------------------------------------------------------
# Parametros reutilizados
# ---------------------------------------------------------------------------
_CLIENTE_ID: dict = {
    "tipo": "string",
    "obrigatorio": True,
    "descricao": "Id (UUID) do cliente, obtido em buscar_clientes. Nunca invente um id.",
}


def _limite(padrao: int, maximo: int, descricao: str = "Quantidade maxima de itens.") -> dict:
    """Parametro inteiro de limite de itens."""
    return {
        "tipo": "integer",
        "minimo": 1,
        "maximo": maximo,
        "descricao": f"{descricao} Padrao {padrao}, maximo {maximo}.",
    }


# ---------------------------------------------------------------------------
# Especificacao das ferramentas (nome = nome da funcao em app.database.consultas)
# ---------------------------------------------------------------------------
_ESPECIFICACAO: dict[str, dict] = {
    "buscar_clientes": {
        "descricao": (
            "Busca clientes da Bulbe. O termo casa (sem diferenciar maiusculas) com nome, e-mail, "
            "CPF (so digitos), numero de instalacao ou codigo de indicacao. Pode filtrar por status e cidade. "
            "Devolve lista resumida: id, nome, email, cpf (mascarado), telefone (mascarado), cidade, uf, "
            "status e etapa_ativacao. Use SEMPRE primeiro para descobrir o id do cliente antes das outras "
            "ferramentas. Sem filtros, lista os clientes mais recentes."
        ),
        "parametros": {
            "termo": {
                "tipo": "string",
                "descricao": "Texto de busca: parte do nome, e-mail, CPF, numero de instalacao ou codigo de indicacao (ex.: MARCOS50).",
            },
            "status": {
                "tipo": "string",
                "enum": STATUS_CLIENTE,
                "descricao": "Filtra pelo status do cliente.",
            },
            "cidade": {"tipo": "string", "descricao": "Filtra pela cidade (ex.: Belo Horizonte, Contagem)."},
            "limite": _limite(20, 50),
        },
    },
    "obter_cliente": {
        "descricao": (
            "Ficha cadastral completa de um cliente: tipo, endereco, distribuidora, numero de instalacao, "
            "usina vinculada, status, codigo de indicacao, se tem acesso ao app e ultimo login no app."
        ),
        "parametros": {"cliente_id": _CLIENTE_ID},
    },
    "obter_ativacao": {
        "descricao": (
            "Jornada de ativacao do cliente (5 etapas, prazo de ate 90 dias): etapa atual, nome e descricao da etapa, "
            "percentual concluido, previsao de conclusao, dias desde o cadastro, situacao de cada etapa e eventos/observacoes."
        ),
        "parametros": {"cliente_id": _CLIENTE_ID},
    },
    "listar_faturas": {
        "descricao": (
            "Faturas de um cliente (mais recentes primeiro): mes de referencia, consumo em kWh, valor sem Bulbe, desconto, "
            "bonus de indicacao, valor total, vencimento, situacao e data de pagamento. Use para 2a via, historico de "
            "pagamentos e faturas vencidas/em aberto de UM cliente."
        ),
        "parametros": {
            "cliente_id": _CLIENTE_ID,
            "situacao": {
                "tipo": "string",
                "enum": SITUACAO_FATURA,
                "descricao": "Filtra pela situacao da fatura.",
            },
            "limite": _limite(12, 24, "Quantidade maxima de faturas."),
        },
    },
    "listar_faturas_vencidas": {
        "descricao": (
            "Faturas vencidas (nao pagas apos o vencimento) de TODOS os clientes, da mais antiga para a mais recente: "
            "fatura_id, cliente_id, cliente_nome, mes de referencia, valor total, vencimento e dias em atraso. "
            "Use para perguntas como 'quais clientes tem fatura vencida' ou inadimplencia em geral."
        ),
        "parametros": {
            "limite": _limite(20, 100, "Quantidade maxima de faturas vencidas."),
        },
    },
    "resumo_economia_cliente": {
        "descricao": (
            "Resumo financeiro do cliente: meses faturados, economia total com desconto, total de bonus de indicacao, "
            "economia total, quantidade de faturas vencidas e valor em aberto."
        ),
        "parametros": {"cliente_id": _CLIENTE_ID},
    },
    "listar_indicacoes": {
        "descricao": (
            "Programa Indique e Ganhe de um cliente: codigo de indicacao, bonus por indicacao (R$ 50), bonus acumulado, "
            "total de indicacoes e a lista (nome do indicado, canal, situacao, bonus, datas)."
        ),
        "parametros": {"cliente_id": _CLIENTE_ID},
    },
    "obter_clube": {
        "descricao": (
            "Situacao do cliente no Clube Bulbe: semanas seguidas na sequencia (meta 5), data da proxima carta, "
            "se tem bonus especial de R$ 50 pendente e as cartas recentes."
        ),
        "parametros": {"cliente_id": _CLIENTE_ID},
    },
    "listar_cupons": {
        "descricao": (
            "Cupons do Clube Bulbe de um cliente, com parceiro (nome e categoria), titulo, codigo, situacao, "
            "data de abertura, validade e data de uso."
        ),
        "parametros": {
            "cliente_id": _CLIENTE_ID,
            "situacao": {
                "tipo": "string",
                "enum": SITUACAO_CUPOM,
                "descricao": "Filtra pela situacao do cupom.",
            },
        },
    },
    "listar_notificacoes": {
        "descricao": (
            "Notificacoes enviadas a um cliente (vencimento, ativacao, clube, indicacao, promocao), com canal "
            "(app, whatsapp, email), data de envio e se foi lida."
        ),
        "parametros": {
            "cliente_id": _CLIENTE_ID,
            "limite": _limite(10, 50, "Quantidade maxima de notificacoes."),
        },
    },
    "listar_atendimentos": {
        "descricao": (
            "Atendimentos (chamados) registrados: canal (whatsapp, email, app, ouvidoria), assunto, descricao, status e datas. "
            "Informe cliente_id para os atendimentos de um cliente, ou omita para listar de todos os clientes."
        ),
        "parametros": {
            "cliente_id": {
                "tipo": "string",
                "descricao": "Id (UUID) do cliente. Opcional: sem ele, lista atendimentos de todos os clientes.",
            },
            "status": {
                "tipo": "string",
                "enum": STATUS_ATENDIMENTO,
                "descricao": "Filtra pelo status do atendimento.",
            },
            "limite": _limite(20, 50, "Quantidade maxima de atendimentos."),
        },
    },
    "listar_adesoes": {
        "descricao": (
            "Pedidos de adesao (novos contratos) feitos pelo app, site ou WhatsApp: nome, cidade, valor da conta atual, "
            "economia mensal estimada, situacao, origem e cliente gerado (quando aprovada)."
        ),
        "parametros": {
            "situacao": {
                "tipo": "string",
                "enum": SITUACAO_ADESAO,
                "descricao": "Filtra pela situacao da adesao.",
            },
            "limite": _limite(20, 50, "Quantidade maxima de adesoes."),
        },
    },
    "listar_usinas": {
        "descricao": "Lista as usinas solares da Bulbe: nome, localizacao, capacidade de geracao (kWh), status e data de ativacao.",
        "parametros": {},
    },
    "listar_parceiros": {
        "descricao": "Lista os parceiros do Clube Bulbe (ex.: Araujo, Inter, Livelo) com categoria e se estao ativos.",
        "parametros": {
            "apenas_ativos": {
                "tipo": "boolean",
                "descricao": "Se true (padrao), traz so os parceiros ativos.",
            },
        },
    },
    "listar_dicas": {
        "descricao": "Lista as dicas de economia de energia exibidas no app, com economia mensal e anual estimada.",
        "parametros": {},
    },
    "metricas_gerais": {
        "descricao": (
            "Metricas gerais da operacao: clientes por status, clientes por etapa de ativacao, faturas vencidas "
            "(quantidade e valor) e em aberto, economia total gerada, indicacoes, Clube Bulbe, adesoes por situacao, "
            "simulacoes nos ultimos 30 dias e uso do app. Use para perguntas de visao geral e totais."
        ),
        "parametros": {},
    },
    "simular_economia": {
        "descricao": (
            "Calcula a economia estimada com a Bulbe (mesmo calculo do simulador do app): desconto de 15%, "
            "bonus de R$ 50 por amigo indicado, economia no periodo e comparativo com/sem Bulbe. Nao grava nada."
        ),
        "parametros": {
            "valor_conta": {
                "tipo": "number",
                "obrigatorio": True,
                "minimo": 0.01,
                "maximo": 1000000,
                "descricao": "Valor medio da conta de luz em reais (maior que zero).",
            },
            "meses": {
                "tipo": "integer",
                "minimo": 1,
                "maximo": 60,
                "descricao": "Periodo da simulacao em meses (1 a 60). Padrao 12.",
            },
            "amigos_indicados": {
                "tipo": "integer",
                "minimo": 0,
                "maximo": 100,
                "descricao": "Quantidade de amigos indicados (0 ou mais). Padrao 0.",
            },
        },
    },
}


def _montar_schema(parametros: dict[str, dict]) -> dict:
    """Converte a especificacao interna de parametros em JSON Schema."""
    propriedades: dict[str, dict] = {}
    obrigatorios: list[str] = []
    for nome, spec in parametros.items():
        prop: dict[str, Any] = {"type": spec["tipo"], "description": spec["descricao"]}
        if "enum" in spec:
            prop["enum"] = list(spec["enum"])
        if "minimo" in spec:
            prop["minimum"] = spec["minimo"]
        if "maximo" in spec:
            prop["maximum"] = spec["maximo"]
        if spec["tipo"] == "string" and "enum" not in spec:
            prop["maxLength"] = LIMITE_CARACTERES_TEXTO
        propriedades[nome] = prop
        if spec.get("obrigatorio"):
            obrigatorios.append(nome)
    schema: dict[str, Any] = {
        "type": "object",
        "properties": propriedades,
        "additionalProperties": False,
    }
    if obrigatorios:
        schema["required"] = obrigatorios
    return schema


# Lista enviada a API (ordem estavel, para nao invalidar o cache de prompt).
TOOLS: list[dict] = [
    {
        "name": nome,
        "description": spec["descricao"],
        "input_schema": _montar_schema(spec["parametros"]),
    }
    for nome, spec in _ESPECIFICACAO.items()
]

NOMES_FERRAMENTAS: list[str] = list(_ESPECIFICACAO.keys())


# ---------------------------------------------------------------------------
# Validacao e conversao das entradas
# ---------------------------------------------------------------------------
class EntradaInvalida(ValueError):
    """Entrada de ferramenta fora do esperado."""


def _converter(nome: str, valor: Any, spec: dict) -> Any:
    """Converte e valida um unico parametro conforme a especificacao."""
    tipo = spec["tipo"]

    if tipo == "string":
        if not isinstance(valor, (str, int, float)) or isinstance(valor, bool):
            raise EntradaInvalida(f"'{nome}' deve ser texto.")
        texto = str(valor).strip()
        if len(texto) > LIMITE_CARACTERES_TEXTO:
            raise EntradaInvalida(f"'{nome}' excede {LIMITE_CARACTERES_TEXTO} caracteres.")
        if "enum" in spec:
            texto = texto.lower()
            if texto not in spec["enum"]:
                raise EntradaInvalida(f"'{nome}' deve ser um destes valores: {', '.join(spec['enum'])}.")
        return texto

    if tipo == "integer":
        if isinstance(valor, bool):
            raise EntradaInvalida(f"'{nome}' deve ser um numero inteiro.")
        try:
            if isinstance(valor, str):
                valor = float(valor.strip().replace(",", "."))
            if isinstance(valor, float):
                if not valor.is_integer():
                    raise EntradaInvalida(f"'{nome}' deve ser um numero inteiro.")
                valor = int(valor)
            if not isinstance(valor, int):
                raise EntradaInvalida(f"'{nome}' deve ser um numero inteiro.")
        except (TypeError, ValueError) as exc:
            if isinstance(exc, EntradaInvalida):
                raise
            raise EntradaInvalida(f"'{nome}' deve ser um numero inteiro.") from exc
        numero: float = valor

    elif tipo == "number":
        if isinstance(valor, bool):
            raise EntradaInvalida(f"'{nome}' deve ser numerico.")
        try:
            if isinstance(valor, str):
                valor = valor.strip().replace("R$", "").strip()
                # "1.234,56" -> "1234.56"; "320,50" -> "320.50"
                if "," in valor:
                    valor = valor.replace(".", "").replace(",", ".")
            valor = float(valor)
        except (TypeError, ValueError) as exc:
            raise EntradaInvalida(f"'{nome}' deve ser numerico.") from exc
        if valor != valor or valor in (float("inf"), float("-inf")):  # NaN / infinito
            raise EntradaInvalida(f"'{nome}' deve ser um numero valido.")
        numero = valor

    elif tipo == "boolean":
        if isinstance(valor, bool):
            return valor
        if isinstance(valor, str) and valor.strip().lower() in ("true", "sim", "1"):
            return True
        if isinstance(valor, str) and valor.strip().lower() in ("false", "nao", "não", "0"):
            return False
        if isinstance(valor, int) and valor in (0, 1):
            return bool(valor)
        raise EntradaInvalida(f"'{nome}' deve ser true ou false.")

    else:  # pragma: no cover - especificacao interna
        raise EntradaInvalida(f"Tipo desconhecido para '{nome}'.")

    if "minimo" in spec and numero < spec["minimo"]:
        raise EntradaInvalida(f"'{nome}' deve ser maior ou igual a {spec['minimo']}.")
    if "maximo" in spec and numero > spec["maximo"]:
        raise EntradaInvalida(f"'{nome}' deve ser menor ou igual a {spec['maximo']}.")
    return valor


def validar_entrada(nome_ferramenta: str, entrada: Any) -> dict[str, Any]:
    """
    Valida a entrada (ja um dict vindo de block.input) e devolve somente os
    argumentos conhecidos, convertidos. Parametros desconhecidos sao ignorados;
    textos vazios em parametros opcionais sao tratados como ausentes.
    """
    if entrada is None:
        entrada = {}
    if not isinstance(entrada, dict):
        raise EntradaInvalida("a entrada deve ser um objeto JSON.")

    parametros: dict[str, dict] = _ESPECIFICACAO[nome_ferramenta]["parametros"]
    argumentos: dict[str, Any] = {}
    for nome, spec in parametros.items():
        valor = entrada.get(nome)
        if isinstance(valor, str) and not valor.strip():
            valor = None
        if valor is None:
            if spec.get("obrigatorio"):
                raise EntradaInvalida(f"o parametro obrigatorio '{nome}' nao foi informado.")
            continue
        argumentos[nome] = _converter(nome, valor, spec)
    return argumentos


# ---------------------------------------------------------------------------
# Mascaramento (LGPD)
# ---------------------------------------------------------------------------
_REGEX_CPF_FORMATADO = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")
_REGEX_TELEFONE_EM_TEXTO = re.compile(r"(?<!\d)(?:\+?55\s?)?\(?\d{2}\)?\s?9?\d{4}[-\s]?\d{4}(?!\d)")
_CAMPOS_TEXTO_LIVRE = {"descricao", "observacao", "mensagem", "assunto", "titulo"}


def _digitos(valor: Any) -> str:
    return re.sub(r"\D", "", str(valor))


def mascarar_cpf(valor: Any) -> Any:
    """'12345678901' -> '***.456.789-**'."""
    if valor is None:
        return None
    digitos = _digitos(valor)
    if len(digitos) == 11:
        return f"***.{digitos[3:6]}.{digitos[6:9]}-**"
    return "***" if digitos else valor


def mascarar_telefone(valor: Any) -> Any:
    """'31987651234' -> '(31) *****-1234'."""
    if valor is None:
        return None
    digitos = _digitos(valor)
    if len(digitos) > 11 and digitos.startswith("55"):
        digitos = digitos[2:]
    if len(digitos) >= 10:
        return f"({digitos[:2]}) *****-{digitos[-4:]}"
    if len(digitos) >= 4:
        return f"*****-{digitos[-4:]}"
    return "*****" if digitos else valor


def _parece_telefone(valor: Any) -> bool:
    texto = str(valor).strip()
    return bool(re.fullmatch(r"[\d\s()+\-.]+", texto)) and len(_digitos(texto)) >= 10


def _mascarar_texto_livre(texto: str) -> str:
    """Mascara CPF formatado e telefones que aparecam no meio de textos livres."""
    texto = _REGEX_CPF_FORMATADO.sub(lambda m: mascarar_cpf(m.group(0)), texto)
    return _REGEX_TELEFONE_EM_TEXTO.sub(lambda m: mascarar_telefone(m.group(0)), texto)


def mascarar_dados(dados: Any) -> Any:
    """Percorre dicts/listas e mascara recursivamente CPF e telefone."""
    if isinstance(dados, list):
        return [mascarar_dados(item) for item in dados]
    if isinstance(dados, tuple):
        return [mascarar_dados(item) for item in dados]
    if not isinstance(dados, dict):
        return dados

    resultado: dict[Any, Any] = {}
    for chave, valor in dados.items():
        nome = str(chave).lower()
        if isinstance(valor, (dict, list, tuple)):
            resultado[chave] = mascarar_dados(valor)
        elif valor is None or isinstance(valor, bool):
            resultado[chave] = valor
        elif "cpf" in nome:
            resultado[chave] = mascarar_cpf(valor)
        elif "telefone" in nome or "celular" in nome:
            resultado[chave] = mascarar_telefone(valor)
        elif "contato" in nome and _parece_telefone(valor):
            resultado[chave] = mascarar_telefone(valor)
        elif nome in _CAMPOS_TEXTO_LIVRE and isinstance(valor, str):
            resultado[chave] = _mascarar_texto_livre(valor)
        else:
            resultado[chave] = valor
    return resultado


# ---------------------------------------------------------------------------
# Serializacao
# ---------------------------------------------------------------------------
def _serializar(dados: Any) -> str:
    """JSON em UTF-8 legivel; corta listas grandes para caber no limite."""
    texto = json.dumps(dados, ensure_ascii=False, default=str)
    if len(texto) <= LIMITE_CARACTERES_RESULTADO:
        return texto
    if isinstance(dados, list):
        quantidade = len(dados)
        while quantidade > 1:
            quantidade //= 2
            parcial = {
                "itens": dados[:quantidade],
                "observacao": f"Resultado cortado: exibindo {quantidade} de {len(dados)} itens. Refine os filtros.",
            }
            texto = json.dumps(parcial, ensure_ascii=False, default=str)
            if len(texto) <= LIMITE_CARACTERES_RESULTADO:
                return texto
    return texto[:LIMITE_CARACTERES_RESULTADO] + " ... [resultado cortado; refine a consulta]"


# ---------------------------------------------------------------------------
# Execucao
# ---------------------------------------------------------------------------
def executar_ferramenta(nome: str, entrada: dict) -> tuple[str, bool]:
    """
    Executa a ferramenta `nome` com a `entrada` (dict vindo de block.input).

    Devolve (conteudo, is_error):
    - (json_mascarado, False) em caso de sucesso;
    - (mensagem, False) quando nada e encontrado (None, lista ou dict vazio; nao e erro),
      ex.: resumo_economia_cliente/listar_indicacoes com cliente inexistente devolvem None;
    - (mensagem, True) quando a consulta levanta ValueError (ex.: simular_economia invalida);
    - (mensagem, True) para ferramenta desconhecida, entrada invalida ou excecao.
    """
    if nome not in _ESPECIFICACAO:
        return (
            f"Ferramenta desconhecida: '{nome}'. Ferramentas disponiveis: {', '.join(NOMES_FERRAMENTAS)}.",
            True,
        )

    try:
        argumentos = validar_entrada(nome, entrada)
    except EntradaInvalida as exc:
        return (f"Entrada invalida para '{nome}': {exc}", True)

    funcao = getattr(consultas, nome, None)
    if not callable(funcao):
        logger.error("Consulta '%s' nao encontrada em app.database.consultas.", nome)
        return (f"A consulta '{nome}' nao esta disponivel no momento.", True)

    try:
        resultado = funcao(**argumentos)
    except ValueError as exc:
        # Regra de negocio violada na consulta (ex.: simular_economia com valor <= 0):
        # a mensagem vem em portugues e e segura para o modelo explicar ao funcionario.
        return (f"Entrada invalida para '{nome}': {exc}", True)
    except Exception as exc:  # noqa: BLE001 - nunca deixar a excecao derrubar o chat
        logger.exception("Erro ao executar a ferramenta '%s'.", nome)
        return (
            f"Erro ao consultar os dados em '{nome}' ({type(exc).__name__}). "
            "Tente novamente ou refine a consulta.",
            True,
        )

    if resultado is None or resultado == [] or resultado == {}:
        filtros = json.dumps(argumentos, ensure_ascii=False, default=str) if argumentos else "nenhum"
        return (
            f"Nenhum registro encontrado em '{nome}' para os parametros informados ({filtros}). "
            "Verifique o id ou refine a busca.",
            False,
        )

    try:
        return (_serializar(mascarar_dados(resultado)), False)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Erro ao serializar o resultado da ferramenta '%s'.", nome)
        return (f"Erro ao preparar o resultado de '{nome}' ({type(exc).__name__}).", True)
