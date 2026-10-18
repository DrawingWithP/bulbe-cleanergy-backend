"""
Camada de Persistencia, consultas somente leitura do banco ficticio da Bulbe.

Regras (secao 1.6 de docs/CONTRATOS.md e secao 1.2 de docs/CONTRATOS-MELHORIAS.md):
- Cada funcao abre a propria sessao com obter_sessao().
- Devolve apenas tipos JSON-serializaveis (dict/list/str/int/float/bool/None).
  Datas viram "AAAA-MM-DD" e instantes viram "AAAA-MM-DDTHH:MM:SSZ" (UTC). Nunca objetos ORM.
- Os dados NAO sao mascarados aqui (o painel mostra completo; o chatbot mascara do lado dele).
- "Nao encontrado" ou filtro invalido: None / lista vazia / pagina vazia (consultas nunca levantam excecao).
- Formato paginado (v2): {"data", "pagina", "por_pagina", "total", "total_paginas"};
  pagina < 1 vira 1, por_pagina fica entre 1 e 100 e total_paginas e sempre >= 1.
- Escritas (v2): registrar_chat, criar_conversa, adicionar_mensagens, registrar_auditoria e
  expurgar_dados_antigos. Todos os instantes gravados saem de agora_utc().
"""
import json
import logging
import math
import re
import unicodedata
from collections import Counter
from collections.abc import Iterator
from datetime import date, datetime, time, timedelta, timezone
from functools import lru_cache
from typing import Any

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.orm import Session, selectinload

from app.database.conexao import obter_sessao
from app.database.modelos import (
    ACOES_AUDITORIA,
    PAPEIS_CHAT,
    SITUACOES_ADESAO,
    SITUACOES_CUPOM,
    SITUACOES_FATURA,
    STATUS_ATENDIMENTO,
    STATUS_CLIENTE,
    TAMANHO_DETALHE_AUDITORIA,
    TAMANHO_TITULO_CONVERSA,
    Adesao,
    Atendimento,
    Ativacao,
    AtivacaoEvento,
    AuditoriaAcesso,
    Carta,
    ChatConversa,
    ChatHistorico,
    ChatMensagem,
    Cliente,
    ClubeStatus,
    Cupom,
    Dica,
    Fatura,
    Funcionario,
    Indicacao,
    Notificacao,
    Parceiro,
    Simulacao,
    Usina,
    agora_utc,
    gerar_uuid,
)
from app.database.seguranca import gerar_hash_senha, verificar_senha

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Regras de negocio (secao 1.4)
# ---------------------------------------------------------------------------
PERCENTUAL_DESCONTO = 15
BONUS_POR_INDICACAO = 50.0
PRAZO_ATIVACAO_DIAS = 90
TOTAL_ETAPAS = 5
PERCENTUAL_POR_ETAPA = {1: 15, 2: 30, 3: 45, 4: 70, 5: 90}
ETAPAS_ATIVACAO = {
    1: ("Cadastro", "Cadastro realizado", "Seu cadastro foi concluído com sucesso."),
    2: ("Documentos", "Documentação sendo analisada",
        "Seus documentos estão em análise. Em breve entraremos em contato."),
    3: ("Solicitação à CEMIG", "Solicitação enviada à CEMIG",
        "A Bulbe protocolou o pedido para a CEMIG liberar sua conexão."),
    4: ("Análise CEMIG", "Em análise pela CEMIG", "Aguardando aprovação da CEMIG."),
    5: ("Energia liberada", "Energia aprovada",
        "Em breve ela será liberada e seu desconto vai começar a aparecer na fatura."),
}
OBSERVACAO_SIMULACAO = (
    "O desconto de 15% não incide sobre a taxa de iluminação pública nem sobre PIS/COFINS."
)
ETAPA5_DESCRICAO = "ativados nos últimos 30 dias"
JANELA_ATIVADOS_DIAS = 30
POR_PAGINA_MAXIMO = 100
TAMANHO_MODELO = 60

@lru_cache(maxsize=1)
def _hash_ficticio() -> str:
    """Hash usado para gastar o mesmo tempo quando o e-mail nao existe (evita enumeracao)."""
    return gerar_hash_senha("senha-inexistente-bulbe")


# ---------------------------------------------------------------------------
# Auxiliares
# ---------------------------------------------------------------------------
def _agora() -> datetime:
    """Instante atual em UTC sem tzinfo (mesma fonte do seed: modelos.agora_utc)."""
    return agora_utc()


def _hoje() -> date:
    """Dia atual derivado de agora_utc(), igual ao seed (evita divergencia perto da meia-noite)."""
    return agora_utc().date()


def _iso(valor: date | datetime | None) -> str | None:
    """date -> 'AAAA-MM-DD'; datetime (UTC) -> 'AAAA-MM-DDTHH:MM:SSZ'; None -> None."""
    if valor is None:
        return None
    if isinstance(valor, datetime):
        if valor.tzinfo is not None:
            valor = valor.astimezone(timezone.utc).replace(tzinfo=None)
        return valor.replace(microsecond=0).isoformat() + "Z"
    return valor.isoformat()


def _dinheiro(valor: float | None) -> float:
    return round(float(valor or 0.0), 2)


def _normalizar(texto: str | None) -> str:
    """Minusculas e sem acentos, para busca tolerante ("joao" casa com "João")."""
    if not texto:
        return ""
    decomposto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in decomposto if not unicodedata.combining(c)).casefold().strip()


def _limitar(limite: int, maximo: int = 100) -> int:
    try:
        return max(1, min(int(limite), maximo))
    except (TypeError, ValueError):
        return 20


def _texto_valido(valor: str | None, permitidos: tuple[str, ...]) -> bool:
    return valor is None or valor in permitidos


def _inteiro(valor: Any, padrao: int = 0, minimo: int | None = 0) -> int:
    """Converte para int (padrao se nao der) e aplica o minimo, se houver."""
    try:
        numero = int(valor)
    except (TypeError, ValueError, OverflowError):
        numero = padrao
    return numero if minimo is None else max(minimo, numero)


def _decimal(valor: Any) -> float:
    """Converte para float >= 0 (0.0 se invalido, negativo, NaN ou infinito)."""
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return 0.0
    return numero if math.isfinite(numero) and numero > 0 else 0.0


def _cortar(texto: Any, tamanho: int) -> str | None:
    """str cortada no tamanho maximo da coluna; None continua None."""
    if texto is None:
        return None
    return str(texto)[:tamanho]


def _usd(valor: float | None) -> float:
    """Valores em dolar com 6 casas (o custo de uma pergunta e fracao de centavo)."""
    return round(float(valor or 0.0), 6)


def _paginacao(pagina: Any, por_pagina: Any, padrao: int = 20) -> tuple[int, int]:
    """Normaliza a paginacao: pagina >= 1 e por_pagina entre 1 e 100."""
    return _inteiro(pagina, 1, 1), min(_inteiro(por_pagina, padrao, 1), POR_PAGINA_MAXIMO)


def _resultado_paginado(data: list[dict], pagina: int, por_pagina: int, total: int) -> dict:
    """Formato paginado padrao da v2 (total_paginas >= 1 mesmo sem resultados)."""
    return {
        "data": data,
        "pagina": pagina,
        "por_pagina": por_pagina,
        "total": int(total),
        "total_paginas": max(1, math.ceil(int(total) / por_pagina)),
    }


def _etapa_filtro(etapa: Any) -> tuple[bool, int | None]:
    """(valida, numero): None e valido (sem filtro); fora de 1..5 ou nao numerico e invalido."""
    if etapa is None:
        return True, None
    try:
        numero = int(etapa)
    except (TypeError, ValueError):
        return False, None
    return 1 <= numero <= TOTAL_ETAPAS, numero


# ---------------------------------------------------------------------------
# Clientes
# ---------------------------------------------------------------------------
def _cliente_resumo(cli: Cliente) -> dict:
    """Item de lista de clientes (buscar_clientes e buscar_clientes_paginado)."""
    return {
        "id": cli.id,
        "nome": cli.nome,
        "email": cli.email,
        "cpf": cli.cpf,
        "telefone": cli.telefone,
        "cidade": cli.cidade,
        "uf": cli.uf,
        "status": cli.status,
        "etapa_ativacao": cli.ativacao.etapa_atual if cli.ativacao else None,
        "criado_em": _iso(cli.criado_em),
    }


def _clientes_filtrados(sessao: Session, termo: str | None, status: str | None,
                        cidade: str | None, etapa: int | None) -> Iterator[Cliente]:
    """
    Clientes que passam nos filtros, ordenados por nome. 'termo' casa (sem diferenciar
    maiusculas/acentos) com nome, e-mail, codigo de indicacao, CPF (so digitos) ou instalacao.
    Quem chama ja validou status e etapa.
    """
    termo_norm = _normalizar(termo)
    # So compara por digitos quando o termo "parece" um documento (ex.: 123.456.789-09)
    digitos = re.sub(r"\D", "", termo or "") if termo and re.fullmatch(r"[\d.\-/\s]+", termo.strip()) else ""
    cidade_norm = _normalizar(cidade)

    consulta = select(Cliente).options(selectinload(Cliente.ativacao)).order_by(Cliente.nome, Cliente.id)
    if status:
        consulta = consulta.where(Cliente.status == status)
    if etapa is not None:
        consulta = consulta.join(Ativacao, Ativacao.cliente_id == Cliente.id).where(Ativacao.etapa_atual == etapa)
    for cli in sessao.scalars(consulta):
        if cidade_norm and cidade_norm not in _normalizar(cli.cidade):
            continue
        if termo_norm:
            if digitos:
                casou = digitos in cli.cpf or digitos in cli.numero_instalacao
            else:
                casou = any(
                    termo_norm in _normalizar(campo)
                    for campo in (cli.nome, cli.email, cli.codigo_indicacao, cli.numero_instalacao)
                )
            if not casou:
                continue
        yield cli


def buscar_clientes(termo: str | None = None, status: str | None = None,
                    cidade: str | None = None, limite: int = 20, etapa: int | None = None) -> list[dict]:
    """
    Busca clientes (ordenado por nome). 'termo' casa (sem diferenciar maiusculas/acentos) com nome,
    e-mail, codigo de indicacao, CPF (so digitos) ou numero de instalacao.
    v2: filtro opcional 'etapa' (1..5) pela etapa_atual da ativacao; etapa invalida -> lista vazia.
    """
    etapa_ok, etapa_num = _etapa_filtro(etapa)
    if not _texto_valido(status, STATUS_CLIENTE) or not etapa_ok:
        return []
    limite = _limitar(limite)
    with obter_sessao() as sessao:
        resultado: list[dict] = []
        for cli in _clientes_filtrados(sessao, termo, status, cidade, etapa_num):
            resultado.append(_cliente_resumo(cli))
            if len(resultado) >= limite:
                break
        return resultado


def buscar_clientes_paginado(termo: str | None = None, status: str | None = None, cidade: str | None = None,
                             etapa: int | None = None, pagina: int = 1, por_pagina: int = 20) -> dict:
    """Mesma busca de buscar_clientes, no formato paginado padrao. Filtro invalido -> pagina vazia."""
    pagina, por_pagina = _paginacao(pagina, por_pagina)
    etapa_ok, etapa_num = _etapa_filtro(etapa)
    if not _texto_valido(status, STATUS_CLIENTE) or not etapa_ok:
        return _resultado_paginado([], pagina, por_pagina, 0)
    with obter_sessao() as sessao:
        todos = list(_clientes_filtrados(sessao, termo, status, cidade, etapa_num))
        inicio = (pagina - 1) * por_pagina
        data = [_cliente_resumo(cli) for cli in todos[inicio:inicio + por_pagina]]
        return _resultado_paginado(data, pagina, por_pagina, len(todos))


def obter_cliente(cliente_id: str) -> dict | None:
    """Ficha cadastral completa do cliente (sem mascaramento)."""
    with obter_sessao() as sessao:
        cli = sessao.get(Cliente, cliente_id, options=[selectinload(Cliente.usina)])
        if cli is None:
            return None
        return {
            "id": cli.id,
            "nome": cli.nome,
            "email": cli.email,
            "cpf": cli.cpf,
            "telefone": cli.telefone,
            "tipo": cli.tipo,
            "endereco": {
                "cep": cli.cep,
                "logradouro": cli.logradouro,
                "numero": cli.numero,
                "complemento": cli.complemento,
                "bairro": cli.bairro,
                "cidade": cli.cidade,
                "uf": cli.uf,
            },
            "distribuidora": cli.distribuidora,
            "numero_instalacao": cli.numero_instalacao,
            "usina": (
                {"id": cli.usina.id, "nome": cli.usina.nome, "localizacao": cli.usina.localizacao}
                if cli.usina else None
            ),
            "status": cli.status,
            "codigo_indicacao": cli.codigo_indicacao,
            "app_acesso_habilitado": cli.app_acesso_habilitado,
            "ultimo_login_app": _iso(cli.ultimo_login_app),
            "criado_em": _iso(cli.criado_em),
            "atualizado_em": _iso(cli.atualizado_em),
        }


def obter_ativacao(cliente_id: str) -> dict | None:
    """Jornada de ativacao em 5 etapas, com o historico de eventos."""
    with obter_sessao() as sessao:
        cli = sessao.get(
            Cliente, cliente_id,
            options=[selectinload(Cliente.ativacao), selectinload(Cliente.eventos_ativacao)],
        )
        if cli is None or cli.ativacao is None:
            return None
        ativacao = cli.ativacao
        etapa_atual = ativacao.etapa_atual
        cancelado = cli.status == "cancelado"
        # Jornada concluida: cliente ativo, ou cancelado depois de a energia ter sido liberada (etapa 5)
        concluida = cli.status == "ativo" or (cancelado and etapa_atual == TOTAL_ETAPAS)
        nome_etapa, titulo, descricao = ETAPAS_ATIVACAO[etapa_atual]
        if cancelado:
            titulo = "Processo encerrado"
            if concluida:
                descricao = ("O cliente cancelou a assinatura depois da conexão; "
                             "a jornada de ativação já tinha sido concluída.")
            else:
                descricao = "O cliente cancelou a assinatura; a jornada de ativação foi interrompida."
        elif concluida:
            titulo = "Energia liberada"
            descricao = "A conexão foi concluída e o desconto da Bulbe já aparece nas faturas."

        etapas = []
        for numero, (nome, titulo_etapa, _) in ETAPAS_ATIVACAO.items():
            if concluida or numero < etapa_atual:
                situacao = "concluida"
            elif numero == etapa_atual and not cancelado:
                situacao = "atual"
            else:
                situacao = "pendente"  # cancelado: nenhuma etapa fica como "atual"
            etapas.append({"numero": numero, "nome": nome, "titulo": titulo_etapa, "situacao": situacao})

        eventos = sorted(cli.eventos_ativacao, key=lambda e: e.ocorrido_em)
        return {
            "cliente_id": cli.id,
            "status_cliente": cli.status,
            "etapa_atual": etapa_atual,
            "total_etapas": TOTAL_ETAPAS,
            "nome_etapa": nome_etapa,
            "titulo": titulo,
            "descricao": descricao,
            "percentual_concluido": 100 if concluida else PERCENTUAL_POR_ETAPA[etapa_atual],
            "prazo_ativacao_dias": PRAZO_ATIVACAO_DIAS,
            "previsao_conclusao": _iso(ativacao.previsao_conclusao),
            "dias_desde_cadastro": max(0, (_hoje() - cli.criado_em.date()).days),
            "atualizado_em": _iso(ativacao.atualizado_em),
            "etapas": etapas,
            "eventos": [
                {"etapa": e.etapa, "observacao": e.observacao, "ocorrido_em": _iso(e.ocorrido_em)}
                for e in eventos
            ],
        }


def _em_ativacao_com_referencia(sessao: Session) -> list[tuple[Cliente, Ativacao, int, int]]:
    """
    Clientes em_ativacao como (cliente, ativacao, dias_na_etapa, dias_desde_cadastro).
    dias_na_etapa conta desde o ultimo movimento da ativacao: o mais recente entre o ultimo
    evento (ativacao_eventos) e ativacoes.atualizado_em.
    """
    hoje = _hoje()
    ultimos_eventos = dict(sessao.execute(
        select(AtivacaoEvento.cliente_id, func.max(AtivacaoEvento.ocorrido_em)).group_by(AtivacaoEvento.cliente_id)
    ).all())
    linhas = sessao.execute(
        select(Cliente, Ativacao)
        .join(Ativacao, Ativacao.cliente_id == Cliente.id)
        .where(Cliente.status == "em_ativacao")
    ).all()
    resultado = []
    for cli, ativacao in linhas:
        referencias = [d for d in (ativacao.atualizado_em, ultimos_eventos.get(cli.id)) if d is not None]
        referencia = max(referencias) if referencias else cli.criado_em
        resultado.append((
            cli,
            ativacao,
            max(0, (hoje - referencia.date()).days),
            max(0, (hoje - cli.criado_em.date()).days),
        ))
    return resultado


def _datas_ativacao(sessao: Session) -> dict[str, tuple[datetime, datetime]]:
    """
    cliente_id -> (cadastro, liberacao da energia) de quem chegou a etapa 5, qualquer que seja o status atual.
    A liberacao e o primeiro evento da etapa 5 (ou ativacoes.atualizado_em, se nao houver evento).
    """
    primeiros = dict(sessao.execute(
        select(AtivacaoEvento.cliente_id, func.min(AtivacaoEvento.ocorrido_em))
        .where(AtivacaoEvento.etapa == TOTAL_ETAPAS)
        .group_by(AtivacaoEvento.cliente_id)
    ).all())
    linhas = sessao.execute(
        select(Cliente.id, Cliente.criado_em, Ativacao.etapa_atual, Ativacao.atualizado_em)
        .join(Ativacao, Ativacao.cliente_id == Cliente.id)
    ).all()
    resultado: dict[str, tuple[datetime, datetime]] = {}
    for cliente_id, criado_em, etapa, atualizado_em in linhas:
        ativado_em = primeiros.get(cliente_id) or (atualizado_em if etapa == TOTAL_ETAPAS else None)
        if ativado_em is not None:
            resultado[cliente_id] = (criado_em, ativado_em)
    return resultado


def listar_clientes_parados(etapa: int | None = None, dias_minimos: int = 30, limite: int = 50) -> list[dict]:
    """
    Clientes em_ativacao sem avancar de etapa ha pelo menos 'dias_minimos' dias (desde o ultimo
    evento/atualizacao da ativacao), do mais parado ao menos parado. Etapa invalida -> lista vazia.
    atrasado = passou dos 90 dias do cadastro.
    """
    etapa_ok, etapa_num = _etapa_filtro(etapa)
    if not etapa_ok:
        return []
    minimo = _inteiro(dias_minimos, 30, 0)
    limite = _limitar(limite)
    with obter_sessao() as sessao:
        itens = [
            item for item in _em_ativacao_com_referencia(sessao)
            if item[2] >= minimo and (etapa_num is None or item[1].etapa_atual == etapa_num)
        ]
        itens.sort(key=lambda item: (-item[2], -item[3], item[0].nome))
        return [
            {
                "cliente_id": cli.id,
                "nome": cli.nome,
                "cidade": cli.cidade,
                "etapa_atual": ativacao.etapa_atual,
                "nome_etapa": ETAPAS_ATIVACAO[ativacao.etapa_atual][0],
                "dias_na_etapa": dias_etapa,
                "dias_desde_cadastro": dias_cadastro,
                "previsao_conclusao": _iso(ativacao.previsao_conclusao),
                "atrasado": dias_cadastro > PRAZO_ATIVACAO_DIAS,
            }
            for cli, ativacao, dias_etapa, dias_cadastro in itens[:limite]
        ]


def resumo_ativacoes() -> dict:
    """
    Resumo do funil de ativacao: clientes em_ativacao por etapa (1..4) e a media de dias parados
    em cada etapa, atrasados (mais de 90 dias do cadastro), ativados nos ultimos 30 dias e tempo
    medio de ativacao (cadastro -> energia liberada, em dias; None se ninguem foi ativado).
    """
    with obter_sessao() as sessao:
        itens = _em_ativacao_com_referencia(sessao)
        por_etapa = {str(e): 0 for e in range(1, TOTAL_ETAPAS)}
        soma_dias = {str(e): 0 for e in range(1, TOTAL_ETAPAS)}
        for _, ativacao, dias_etapa, _ in itens:
            chave = str(ativacao.etapa_atual)
            if chave in por_etapa:
                por_etapa[chave] += 1
                soma_dias[chave] += dias_etapa
        datas = _datas_ativacao(sessao)
        corte = _agora() - timedelta(days=JANELA_ATIVADOS_DIAS)
        tempos = [max(0, (ativado.date() - criado.date()).days) for criado, ativado in datas.values()]
        return {
            "em_ativacao": len(itens),
            "por_etapa": por_etapa,
            "dias_medios_na_etapa": {
                chave: round(soma_dias[chave] / por_etapa[chave], 1) if por_etapa[chave] else 0.0
                for chave in por_etapa
            },
            "atrasados_90_dias": sum(1 for item in itens if item[3] > PRAZO_ATIVACAO_DIAS),
            "ativados_30_dias": sum(1 for _, ativado in datas.values() if ativado >= corte),
            "tempo_medio_ativacao_dias": round(sum(tempos) / len(tempos), 1) if tempos else None,
        }


# ---------------------------------------------------------------------------
# Faturas e economia
# ---------------------------------------------------------------------------
def _fatura_para_dict(f: Fatura) -> dict:
    return {
        "id": f.id,
        "cliente_id": f.cliente_id,
        "mes_referencia": f.mes_referencia,
        "consumo_kwh": round(float(f.consumo_kwh), 1),
        "valor_sem_bulbe": _dinheiro(f.valor_sem_bulbe),
        "desconto": _dinheiro(f.desconto),
        "bonus_indicacao": _dinheiro(f.bonus_indicacao),
        "bonus_clube": _dinheiro(f.bonus_clube),
        "valor_total": _dinheiro(f.valor_total),
        "vencimento": _iso(f.vencimento),
        "situacao": f.situacao,
        "pago_em": _iso(f.pago_em),
    }


def listar_faturas(cliente_id: str, situacao: str | None = None, limite: int = 12) -> list[dict]:
    """Faturas do cliente, da mais recente para a mais antiga."""
    if not _texto_valido(situacao, SITUACOES_FATURA):
        return []
    with obter_sessao() as sessao:
        consulta = (
            select(Fatura)
            .where(Fatura.cliente_id == cliente_id)
            .order_by(Fatura.mes_referencia.desc())
            .limit(_limitar(limite, 120))
        )
        if situacao:
            consulta = consulta.where(Fatura.situacao == situacao)
        return [_fatura_para_dict(f) for f in sessao.scalars(consulta)]


def listar_faturas_vencidas(limite: int = 20) -> list[dict]:
    """
    Faturas com situacao "vencida" de todos os clientes, da mais antiga para a mais recente
    (pedido do lider, fora da secao 1.6 original).
    """
    hoje = _hoje()
    with obter_sessao() as sessao:
        consulta = (
            select(Fatura, Cliente.nome)
            .join(Cliente, Cliente.id == Fatura.cliente_id)
            .where(Fatura.situacao == "vencida")
            .order_by(Fatura.vencimento.asc(), Cliente.nome.asc())
            .limit(_limitar(limite))
        )
        return [
            {
                "fatura_id": f.id,
                "cliente_id": f.cliente_id,
                "cliente_nome": nome,
                "mes_referencia": f.mes_referencia,
                "bonus_clube": _dinheiro(f.bonus_clube),
                "valor_total": _dinheiro(f.valor_total),
                "vencimento": _iso(f.vencimento),
                "dias_em_atraso": max(0, (hoje - f.vencimento).days),
            }
            for f, nome in sessao.execute(consulta).all()
        ]


def resumo_economia_cliente(cliente_id: str) -> dict | None:
    """
    Totais de economia do cliente a partir das faturas. Cliente inexistente -> None
    (regra geral do contrato para "nao encontrado").
    v2: bonus_clube_total (bonus especial do Clube Bulbe), tambem somado em economia_total.
    """
    with obter_sessao() as sessao:
        if sessao.get(Cliente, cliente_id) is None:
            return None
        faturas = list(sessao.scalars(select(Fatura).where(Fatura.cliente_id == cliente_id)))
        desconto = sum(f.desconto for f in faturas)
        bonus = sum(f.bonus_indicacao for f in faturas)
        bonus_clube = sum(f.bonus_clube or 0.0 for f in faturas)
        return {
            "cliente_id": cliente_id,
            "meses_faturados": len(faturas),
            "economia_total_desconto": _dinheiro(desconto),
            "bonus_indicacao_total": _dinheiro(bonus),
            "bonus_clube_total": _dinheiro(bonus_clube),
            "economia_total": _dinheiro(desconto + bonus + bonus_clube),
            "faturas_vencidas": sum(1 for f in faturas if f.situacao == "vencida"),
            "valor_em_aberto": _dinheiro(
                sum(f.valor_total for f in faturas if f.situacao in ("em_aberto", "vencida"))
            ),
        }


# ---------------------------------------------------------------------------
# Indicacoes, Clube Bulbe e cupons
# ---------------------------------------------------------------------------
def listar_indicacoes(cliente_id: str) -> dict | None:
    """
    Indicacoes feitas pelo cliente (Indique e Ganhe). bonus_acumulado = soma dos bonus das
    indicacoes que aderiram (creditadas ou a creditar na proxima fatura). Cliente inexistente -> None.
    """
    with obter_sessao() as sessao:
        cli = sessao.get(Cliente, cliente_id)
        if cli is None:
            return None
        indicacoes = list(sessao.scalars(
            select(Indicacao).where(Indicacao.cliente_id == cliente_id).order_by(Indicacao.criado_em.desc())
        ))
        return {
            "codigo_indicacao": cli.codigo_indicacao,
            "bonus_por_indicacao": BONUS_POR_INDICACAO,
            "bonus_acumulado": _dinheiro(sum(i.bonus for i in indicacoes if i.situacao == "aderiu")),
            "total": len(indicacoes),
            "data": [
                {
                    "id": i.id,
                    "nome_indicado": i.nome_indicado,
                    "contato_indicado": i.contato_indicado,
                    "canal": i.canal,
                    "situacao": i.situacao,
                    "bonus": _dinheiro(i.bonus),
                    "creditado_em": _iso(i.creditado_em),
                    "criado_em": _iso(i.criado_em),
                }
                for i in indicacoes
            ],
        }


def obter_clube(cliente_id: str) -> dict | None:
    """Situacao do cliente no Clube Bulbe e as 5 cartas mais recentes."""
    with obter_sessao() as sessao:
        clube = sessao.get(ClubeStatus, cliente_id)
        if clube is None:
            return None
        cartas = sessao.scalars(
            select(Carta).where(Carta.cliente_id == cliente_id).order_by(Carta.semana.desc()).limit(5)
        )
        return {
            "cliente_id": cliente_id,
            "semanas_sequencia": clube.semanas_sequencia,
            "meta_sequencia": clube.meta_sequencia,
            "proxima_carta_em": _iso(clube.proxima_carta_em),
            "bonus_especial_pendente": clube.bonus_especial_pendente,
            "cartas_recentes": [
                {
                    "id": c.id,
                    "semana": c.semana,
                    "tipo": c.tipo,
                    "situacao": c.situacao,
                    "disponivel_em": _iso(c.disponivel_em),
                    "aberta_em": _iso(c.aberta_em),
                    "cupom_id": c.cupom_id,
                }
                for c in cartas
            ],
        }


def listar_cupons(cliente_id: str, situacao: str | None = None) -> list[dict]:
    """Cupons do cliente (mais recentes primeiro), com o parceiro de cada um."""
    if not _texto_valido(situacao, SITUACOES_CUPOM):
        return []
    with obter_sessao() as sessao:
        consulta = (
            select(Cupom)
            .options(selectinload(Cupom.parceiro))
            .where(Cupom.cliente_id == cliente_id)
            .order_by(Cupom.aberto_em.desc())
        )
        if situacao:
            consulta = consulta.where(Cupom.situacao == situacao)
        return [
            {
                "id": c.id,
                "carta_id": c.carta_id,
                "titulo": c.titulo,
                "descricao": c.descricao,
                "codigo": c.codigo,
                "situacao": c.situacao,
                "aberto_em": _iso(c.aberto_em),
                "valido_ate": _iso(c.valido_ate),
                "usado_em": _iso(c.usado_em),
                "parceiro": (
                    {"id": c.parceiro.id, "nome": c.parceiro.nome, "categoria": c.parceiro.categoria}
                    if c.parceiro else None
                ),
            }
            for c in sessao.scalars(consulta)
        ]


# ---------------------------------------------------------------------------
# Notificacoes, atendimentos e adesoes
# ---------------------------------------------------------------------------
def listar_notificacoes(cliente_id: str, limite: int = 10) -> list[dict]:
    """Notificacoes enviadas ao cliente, das mais recentes para as mais antigas."""
    with obter_sessao() as sessao:
        consulta = (
            select(Notificacao)
            .where(Notificacao.cliente_id == cliente_id)
            .order_by(Notificacao.enviada_em.desc())
            .limit(_limitar(limite))
        )
        return [
            {
                "id": n.id,
                "tipo": n.tipo,
                "titulo": n.titulo,
                "mensagem": n.mensagem,
                "canal": n.canal,
                "enviada_em": _iso(n.enviada_em),
                "lida": n.lida,
            }
            for n in sessao.scalars(consulta)
        ]


def _atendimento_para_dict(a: Atendimento, cliente_nome: str) -> dict:
    return {
        "id": a.id,
        "cliente_id": a.cliente_id,
        "cliente_nome": cliente_nome,
        "canal": a.canal,
        "assunto": a.assunto,
        "descricao": a.descricao,
        "status": a.status,
        "criado_em": _iso(a.criado_em),
        "resolvido_em": _iso(a.resolvido_em),
    }


def _filtros_atendimento(cliente_id: str | None, status: str | None) -> list[Any]:
    filtros: list[Any] = []
    if cliente_id is not None:
        filtros.append(Atendimento.cliente_id == cliente_id)
    if status:
        filtros.append(Atendimento.status == status)
    return filtros


def listar_atendimentos(cliente_id: str | None = None, status: str | None = None,
                        limite: int = 20) -> list[dict]:
    """Atendimentos (de um cliente ou de todos), mais recentes primeiro, com o nome do cliente."""
    if not _texto_valido(status, STATUS_ATENDIMENTO):
        return []
    with obter_sessao() as sessao:
        consulta = (
            select(Atendimento, Cliente.nome)
            .join(Cliente, Cliente.id == Atendimento.cliente_id)
            .where(*_filtros_atendimento(cliente_id, status))
            .order_by(Atendimento.criado_em.desc(), Atendimento.id.desc())
            .limit(_limitar(limite))
        )
        return [_atendimento_para_dict(a, nome) for a, nome in sessao.execute(consulta).all()]


def listar_atendimentos_paginado(cliente_id: str | None = None, status: str | None = None,
                                 pagina: int = 1, por_pagina: int = 20) -> dict:
    """Atendimentos no formato paginado padrao (mais recentes primeiro, itens com cliente_nome)."""
    pagina, por_pagina = _paginacao(pagina, por_pagina)
    if not _texto_valido(status, STATUS_ATENDIMENTO):
        return _resultado_paginado([], pagina, por_pagina, 0)
    filtros = _filtros_atendimento(cliente_id, status)
    with obter_sessao() as sessao:
        total = sessao.scalar(select(func.count()).select_from(Atendimento).where(*filtros)) or 0
        consulta = (
            select(Atendimento, Cliente.nome)
            .join(Cliente, Cliente.id == Atendimento.cliente_id)
            .where(*filtros)
            .order_by(Atendimento.criado_em.desc(), Atendimento.id.desc())
            .offset((pagina - 1) * por_pagina)
            .limit(por_pagina)
        )
        data = [_atendimento_para_dict(a, nome) for a, nome in sessao.execute(consulta).all()]
        return _resultado_paginado(data, pagina, por_pagina, total)


def _adesao_para_dict(a: Adesao) -> dict:
    return {
        "id": a.id,
        "nome": a.nome,
        "email": a.email,
        "cpf": a.cpf,
        "telefone": a.telefone,
        "cidade": a.cidade,
        "uf": a.uf,
        "distribuidora": a.distribuidora,
        "numero_instalacao": a.numero_instalacao,
        "valor_conta_atual": _dinheiro(a.valor_conta_atual) if a.valor_conta_atual is not None else None,
        "economia_mensal_estimada": (
            _dinheiro(a.economia_mensal_estimada) if a.economia_mensal_estimada is not None else None
        ),
        "situacao": a.situacao,
        "origem": a.origem,
        "cliente_id": a.cliente_id,
        "criado_em": _iso(a.criado_em),
    }


def listar_adesoes(situacao: str | None = None, limite: int = 20) -> list[dict]:
    """Solicitacoes de adesao (app/site/WhatsApp), mais recentes primeiro."""
    if not _texto_valido(situacao, SITUACOES_ADESAO):
        return []
    with obter_sessao() as sessao:
        consulta = select(Adesao).order_by(Adesao.criado_em.desc(), Adesao.id).limit(_limitar(limite))
        if situacao:
            consulta = consulta.where(Adesao.situacao == situacao)
        return [_adesao_para_dict(a) for a in sessao.scalars(consulta)]


def listar_adesoes_paginado(situacao: str | None = None, pagina: int = 1, por_pagina: int = 20) -> dict:
    """Adesoes no formato paginado padrao (mais recentes primeiro)."""
    pagina, por_pagina = _paginacao(pagina, por_pagina)
    if not _texto_valido(situacao, SITUACOES_ADESAO):
        return _resultado_paginado([], pagina, por_pagina, 0)
    filtros = [Adesao.situacao == situacao] if situacao else []
    with obter_sessao() as sessao:
        total = sessao.scalar(select(func.count()).select_from(Adesao).where(*filtros)) or 0
        consulta = (
            select(Adesao)
            .where(*filtros)
            .order_by(Adesao.criado_em.desc(), Adesao.id)
            .offset((pagina - 1) * por_pagina)
            .limit(por_pagina)
        )
        data = [_adesao_para_dict(a) for a in sessao.scalars(consulta)]
        return _resultado_paginado(data, pagina, por_pagina, total)


# ---------------------------------------------------------------------------
# Catalogos: usinas, parceiros e dicas
# ---------------------------------------------------------------------------
def listar_usinas() -> list[dict]:
    """Usinas com a quantidade de clientes ativos vinculados."""
    with obter_sessao() as sessao:
        contagem = dict(
            sessao.execute(
                select(Cliente.usina_id, func.count())
                .where(Cliente.status == "ativo", Cliente.usina_id.is_not(None))
                .group_by(Cliente.usina_id)
            ).all()
        )
        return [
            {
                "id": u.id,
                "nome": u.nome,
                "localizacao": u.localizacao,
                "capacidade_geracao_kwh": round(float(u.capacidade_geracao_kwh), 2),
                "status": u.status,
                "data_ativacao": _iso(u.data_ativacao),
                "clientes_ativos": int(contagem.get(u.id, 0)),
            }
            for u in sessao.scalars(select(Usina).order_by(Usina.id))
        ]


def listar_parceiros(apenas_ativos: bool = True) -> list[dict]:
    """Parceiros do Clube Bulbe."""
    with obter_sessao() as sessao:
        consulta = select(Parceiro).order_by(Parceiro.nome)
        if apenas_ativos:
            consulta = consulta.where(Parceiro.ativo.is_(True))
        return [
            {
                "id": p.id,
                "nome": p.nome,
                "categoria": p.categoria,
                "logo_url": p.logo_url,
                "ativo": p.ativo,
                "criado_em": _iso(p.criado_em),
            }
            for p in sessao.scalars(consulta)
        ]


def listar_dicas() -> list[dict]:
    """Dicas de economia na ordem do carrossel do app."""
    with obter_sessao() as sessao:
        return [
            {
                "id": d.id,
                "titulo": d.titulo,
                "descricao": d.descricao,
                "economia_mensal": _dinheiro(d.economia_mensal),
                "economia_anual": _dinheiro(d.economia_anual),
                "ordem": d.ordem,
            }
            for d in sessao.scalars(select(Dica).order_by(Dica.ordem))
        ]


# ---------------------------------------------------------------------------
# Metricas e simulador
# ---------------------------------------------------------------------------
def _contar_por(sessao, coluna, valores: tuple[str, ...]) -> dict[str, int]:  # type: ignore[no-untyped-def]
    linhas = dict(sessao.execute(select(coluna, func.count()).group_by(coluna)).all())
    return {valor: int(linhas.get(valor, 0)) for valor in valores}


def metricas_gerais() -> dict:
    """
    Numeros gerais para a visao geral do painel.
    v2: ativacao_por_etapa["1".."4"] conta os clientes em_ativacao em cada etapa e ["5"] conta os
    clientes ATIVADOS nos ultimos 30 dias (ativacao_etapa5_descricao explica isso);
    clube.bonus_pagos soma faturas.bonus_clube; economia_total_gerada inclui o bonus do Clube.
    """
    agora = _agora()
    limite_30_dias = agora - timedelta(days=30)
    with obter_sessao() as sessao:
        clientes = _contar_por(sessao, Cliente.status, STATUS_CLIENTE)

        # Funil de ativacao: etapas 1-4 = clientes com status em_ativacao; etapa 5 = ativados em 30 dias
        por_etapa = dict(
            sessao.execute(
                select(Ativacao.etapa_atual, func.count())
                .join(Cliente, Cliente.id == Ativacao.cliente_id)
                .where(Cliente.status == "em_ativacao")
                .group_by(Ativacao.etapa_atual)
            ).all()
        )
        por_etapa[TOTAL_ETAPAS] = sum(
            1 for _, ativado_em in _datas_ativacao(sessao).values() if ativado_em >= limite_30_dias
        )

        vencidas, valor_vencido = sessao.execute(
            select(func.count(), func.coalesce(func.sum(Fatura.valor_total), 0.0))
            .select_from(Fatura)
            .where(Fatura.situacao == "vencida")
        ).one()
        em_aberto = sessao.scalar(
            select(func.count()).select_from(Fatura).where(Fatura.situacao == "em_aberto")
        ) or 0
        economia = sessao.scalar(
            select(func.coalesce(
                func.sum(Fatura.desconto + Fatura.bonus_indicacao + func.coalesce(Fatura.bonus_clube, 0.0)), 0.0
            )).select_from(Fatura)
        ) or 0.0
        bonus_pagos = sessao.scalar(
            select(func.coalesce(func.sum(Fatura.bonus_clube), 0.0)).select_from(Fatura)
        ) or 0.0

        indicacoes = _contar_por(sessao, Indicacao.situacao, ("pendente", "aderiu", "expirada"))
        cupons = _contar_por(sessao, Cupom.situacao, SITUACOES_CUPOM)
        com_sequencia = sessao.scalar(
            select(func.count()).select_from(ClubeStatus).where(ClubeStatus.semanas_sequencia > 0)
        ) or 0
        adesoes = _contar_por(sessao, Adesao.situacao, SITUACOES_ADESAO)
        simulacoes = sessao.scalar(
            select(func.count()).select_from(Simulacao).where(Simulacao.criado_em >= limite_30_dias)
        ) or 0
        com_acesso = sessao.scalar(
            select(func.count()).select_from(Cliente).where(Cliente.app_acesso_habilitado.is_(True))
        ) or 0
        logins = sessao.scalar(
            select(func.count()).select_from(Cliente).where(Cliente.ultimo_login_app >= limite_30_dias)
        ) or 0

        return {
            "clientes": {"total": sum(clientes.values()), **clientes},
            "ativacao_por_etapa": {str(e): int(por_etapa.get(e, 0)) for e in range(1, TOTAL_ETAPAS + 1)},
            "ativacao_etapa5_descricao": ETAPA5_DESCRICAO,
            "faturas": {
                "vencidas": int(vencidas),
                "valor_vencido": _dinheiro(valor_vencido),
                "em_aberto": int(em_aberto),
            },
            "economia_total_gerada": _dinheiro(economia),
            "indicacoes": {
                "total": sum(indicacoes.values()),
                "aderiu": indicacoes["aderiu"],
                "pendente": indicacoes["pendente"],
            },
            "clube": {
                "clientes_com_sequencia": int(com_sequencia),
                "cupons_ativos": cupons["ativo"],
                "cupons_usados": cupons["usado"],
                "bonus_pagos": _dinheiro(bonus_pagos),
            },
            "adesoes": adesoes,
            "simulacoes_30_dias": int(simulacoes),
            "app": {"clientes_com_acesso": int(com_acesso), "logins_ultimos_30_dias": int(logins)},
        }


def simular_economia(valor_conta: float, meses: int = 12, amigos_indicados: int = 0) -> dict:
    """
    Calculo puro (nao acessa o banco), mesmo formato de POST /v1/simulacoes.
    Entradas invalidas (valor <= 0, meses fora de 1..60, amigos < 0) levantam ValueError
    com mensagem em portugues (equivale ao 400 da API).
    """
    try:
        valor = float(valor_conta)
        meses = int(meses)
        amigos = int(amigos_indicados)
    except (TypeError, ValueError) as erro:
        raise ValueError("valor_conta, meses e amigos_indicados devem ser numéricos.") from erro
    if valor <= 0:
        raise ValueError("O valor da conta deve ser maior que zero.")
    if not 1 <= meses <= 60:
        raise ValueError("O período deve estar entre 1 e 60 meses.")
    if amigos < 0:
        raise ValueError("A quantidade de amigos indicados não pode ser negativa.")

    desconto_mensal = round(valor * PERCENTUAL_DESCONTO / 100, 2)
    desconto_periodo = round(desconto_mensal * meses, 2)
    bonus = round(amigos * BONUS_POR_INDICACAO, 2)
    nova_conta = round(max(0.0, valor - desconto_mensal), 2)
    return {
        "valor_conta": round(valor, 2),
        "meses": meses,
        "amigos_indicados": amigos,
        "percentual_desconto": PERCENTUAL_DESCONTO,
        "desconto_mensal": desconto_mensal,
        "desconto_periodo": desconto_periodo,
        "bonus_indicacoes": bonus,
        "economia_total": round(desconto_periodo + bonus, 2),
        "nova_conta_mensal": nova_conta,
        "comparativo": {
            "sem_bulbe_mensal": round(valor, 2),
            "com_bulbe_mensal": nova_conta,
            "sem_bulbe_periodo": round(valor * meses, 2),
            "com_bulbe_periodo": round(nova_conta * meses, 2),
        },
        "observacao": OBSERVACAO_SIMULACAO,
    }


# ---------------------------------------------------------------------------
# Funcionarios e auditoria do chatbot
# ---------------------------------------------------------------------------
def _funcionario_para_dict(f: Funcionario) -> dict:
    return {"id": f.id, "nome": f.nome, "email": f.email, "perfil": f.perfil}


def autenticar_funcionario(email: str, senha: str) -> dict | None:
    """Confere e-mail (sem diferenciar maiusculas) e senha. Devolve {id, nome, email, perfil} se ok e ativo."""
    email_norm = (email or "").strip().lower()
    with obter_sessao() as sessao:
        funcionario = sessao.scalar(select(Funcionario).where(func.lower(Funcionario.email) == email_norm))
        if funcionario is None:
            verificar_senha(senha or "", _hash_ficticio())  # mesmo custo de tempo
            return None
        if not verificar_senha(senha or "", funcionario.senha_hash) or not funcionario.ativo:
            return None
        return _funcionario_para_dict(funcionario)


def obter_funcionario(funcionario_id: int) -> dict | None:
    """{id, nome, email, perfil} do funcionario ativo; None se nao existe ou esta inativo."""
    with obter_sessao() as sessao:
        funcionario = sessao.get(Funcionario, funcionario_id)
        if funcionario is None or not funcionario.ativo:
            return None
        return _funcionario_para_dict(funcionario)


def obter_funcionario_por_email(email: str) -> dict | None:
    """
    {id, nome, email, perfil, ativo} do funcionario com aquele e-mail (sem diferenciar maiusculas,
    ignorando espacos nas pontas), inclusive inativos; None se nao existe. Usado pelo painel para
    preencher funcionario_id na auditoria de login falho.
    """
    email_norm = (email or "").strip().lower() if isinstance(email, str) else ""
    if not email_norm:
        return None
    with obter_sessao() as sessao:
        funcionario = sessao.scalar(select(Funcionario).where(func.lower(Funcionario.email) == email_norm))
        if funcionario is None:
            return None
        return {**_funcionario_para_dict(funcionario), "ativo": bool(funcionario.ativo)}


def registrar_chat(funcionario_id: int, pergunta: str, resposta: str, ferramentas_usadas: list[str], *,
                   conversa_id: str | None = None, modelo: str | None = None, uso: dict | None = None,
                   duracao_ms: int | None = None) -> None:
    """
    Grava uma troca do chatbot (auditoria/LGPD e metricas de uso).
    v2 (parametros opcionais, so por nome): conversa_id, modelo, duracao_ms e
    uso = {input_tokens, output_tokens, cache_read_tokens, cache_creation_tokens, custo_estimado_usd}.
    Valores de uso ausentes ou invalidos viram 0. Uma conversa_id que nao existe (ex.: ja expurgada)
    e gravada como nula, para a auditoria nunca falhar por causa dela.
    """
    uso = uso if isinstance(uso, dict) else {}
    with obter_sessao() as sessao:
        if conversa_id is not None and sessao.get(ChatConversa, str(conversa_id)) is None:
            logger.warning("registrar_chat: conversa %s nao existe; gravando sem conversa_id.", conversa_id)
            conversa_id = None
        sessao.add(ChatHistorico(
            funcionario_id=funcionario_id,
            pergunta=pergunta,
            resposta=resposta,
            ferramentas_usadas=json.dumps(list(ferramentas_usadas or []), ensure_ascii=False),
            criado_em=_agora(),
            conversa_id=str(conversa_id) if conversa_id is not None else None,
            modelo=_cortar(modelo, TAMANHO_MODELO) or None,
            input_tokens=_inteiro(uso.get("input_tokens")),
            output_tokens=_inteiro(uso.get("output_tokens")),
            cache_read_tokens=_inteiro(uso.get("cache_read_tokens")),
            cache_creation_tokens=_inteiro(uso.get("cache_creation_tokens")),
            custo_estimado_usd=_decimal(uso.get("custo_estimado_usd")),
            duracao_ms=_inteiro(duracao_ms) if duracao_ms is not None else None,
        ))


# ---------------------------------------------------------------------------
# Chat: conversas guardadas no servidor (v2)
# ---------------------------------------------------------------------------
def _conversa_para_dict(c: ChatConversa) -> dict:
    return {
        "id": c.id,
        "titulo": c.titulo,
        "criado_em": _iso(c.criado_em),
        "atualizado_em": _iso(c.atualizado_em),
    }


def criar_conversa(funcionario_id: int, titulo: str) -> dict:
    """
    Cria uma conversa vazia do funcionario. O titulo e cortado em 120 caracteres
    (vazio vira "Nova conversa"). Funcionario inexistente -> ValueError.
    """
    titulo_limpo = (str(titulo or "")).strip()[:TAMANHO_TITULO_CONVERSA] or "Nova conversa"
    agora = _agora()
    with obter_sessao() as sessao:
        if sessao.get(Funcionario, funcionario_id) is None:
            raise ValueError(f"Funcionário {funcionario_id} não existe.")
        conversa = ChatConversa(
            id=gerar_uuid(), funcionario_id=funcionario_id, titulo=titulo_limpo,
            criado_em=agora, atualizado_em=agora,
        )
        sessao.add(conversa)
        return _conversa_para_dict(conversa)


def listar_conversas(funcionario_id: int, limite: int = 20) -> list[dict]:
    """Conversas do funcionario, das mais recentes (atualizado_em) para as mais antigas, com total_mensagens."""
    with obter_sessao() as sessao:
        contagem = (
            select(ChatMensagem.conversa_id, func.count().label("total"))
            .group_by(ChatMensagem.conversa_id)
            .subquery()
        )
        consulta = (
            select(ChatConversa, func.coalesce(contagem.c.total, 0))
            .outerjoin(contagem, contagem.c.conversa_id == ChatConversa.id)
            .where(ChatConversa.funcionario_id == funcionario_id)
            .order_by(ChatConversa.atualizado_em.desc(), ChatConversa.criado_em.desc(), ChatConversa.id)
            .limit(_limitar(limite))
        )
        return [
            {**_conversa_para_dict(conversa), "total_mensagens": int(total)}
            for conversa, total in sessao.execute(consulta).all()
        ]


def _carregar_conteudo(conteudo_json: str) -> Any:
    """json.loads do conteudo gravado (se, por algum motivo, nao for JSON valido, devolve o texto cru)."""
    try:
        return json.loads(conteudo_json)
    except (TypeError, ValueError):
        logger.warning("chat_mensagens com conteudo_json invalido; devolvendo o texto cru.")
        return conteudo_json


def obter_conversa(conversa_id: str, funcionario_id: int) -> dict | None:
    """
    Conversa com todas as mensagens em ordem. None se nao existe OU se pertence a outro funcionario.
    "conteudo" e o json.loads(conteudo_json): identico ao que foi gravado, pronto para reenviar a API.
    """
    with obter_sessao() as sessao:
        conversa = sessao.get(ChatConversa, str(conversa_id), options=[selectinload(ChatConversa.mensagens)])
        if conversa is None or conversa.funcionario_id != _inteiro(funcionario_id, -1, None):
            return None
        return {
            **_conversa_para_dict(conversa),
            "mensagens": [
                {
                    "ordem": m.ordem,
                    "papel": m.papel,
                    "conteudo": _carregar_conteudo(m.conteudo_json),
                    "texto": m.texto or "",
                    "criado_em": _iso(m.criado_em),
                }
                for m in sorted(conversa.mensagens, key=lambda m: m.ordem)
            ],
        }


def adicionar_mensagens(conversa_id: str, mensagens: list[dict]) -> None:
    """
    Acrescenta mensagens no fim da conversa (ordem crescente, continuando da ultima) e atualiza
    atualizado_em. O historico e so de acrescimo: nenhuma mensagem antiga e alterada.
    Cada item: {papel: "user"|"assistant", conteudo: list|str, texto: str}; conteudo_json =
    json.dumps(conteudo, ensure_ascii=False). Papel invalido, item sem conteudo ou conversa
    inexistente -> ValueError (nada e gravado).
    """
    preparadas: list[tuple[str, str, str]] = []
    for item in mensagens or []:
        if not isinstance(item, dict) or "conteudo" not in item:
            raise ValueError("Cada mensagem precisa ser um dict com 'papel', 'conteudo' e 'texto'.")
        papel = item.get("papel")
        if papel not in PAPEIS_CHAT:
            raise ValueError(f"Papel inválido: {papel!r} (use 'user' ou 'assistant').")
        texto = item.get("texto")
        preparadas.append((papel, json.dumps(item["conteudo"], ensure_ascii=False), "" if texto is None else str(texto)))
    if not preparadas:
        return

    agora = _agora()
    with obter_sessao() as sessao:
        conversa = sessao.get(ChatConversa, str(conversa_id))
        if conversa is None:
            raise ValueError(f"Conversa {conversa_id} não existe.")
        ultima = sessao.scalar(
            select(func.max(ChatMensagem.ordem)).where(ChatMensagem.conversa_id == conversa.id)
        ) or 0
        for posicao, (papel, conteudo_json, texto) in enumerate(preparadas, start=1):
            sessao.add(ChatMensagem(
                conversa_id=conversa.id, ordem=ultima + posicao, papel=papel,
                conteudo_json=conteudo_json, texto=texto, criado_em=agora,
            ))
        conversa.atualizado_em = agora


def metricas_uso_chatbot(dias: int = 30) -> dict:
    """
    Uso e custo estimado do chatbot nos ultimos 'dias' dias de calendario (hoje incluso, 1 a 3650),
    a partir de chat_historico. por_dia traz todos os dias do periodo (inclusive os sem uso).
    duracao_media_ms considera so as trocas com duracao registrada (0 se nenhuma).
    """
    dias = min(_inteiro(dias, 30, 1), 3650)
    hoje = _hoje()
    inicio = hoje - timedelta(days=dias - 1)
    corte = datetime.combine(inicio, time.min)
    with obter_sessao() as sessao:
        linhas = sessao.execute(
            select(
                ChatHistorico.funcionario_id, ChatHistorico.conversa_id, ChatHistorico.ferramentas_usadas,
                ChatHistorico.input_tokens, ChatHistorico.output_tokens, ChatHistorico.cache_read_tokens,
                ChatHistorico.cache_creation_tokens, ChatHistorico.custo_estimado_usd,
                ChatHistorico.duracao_ms, ChatHistorico.criado_em,
            ).where(ChatHistorico.criado_em >= corte)
        ).all()
        nomes = dict(sessao.execute(select(Funcionario.id, Funcionario.nome)).all())

    totais = Counter()
    ferramentas: Counter[str] = Counter()
    por_funcionario: dict[int, dict] = {}
    por_dia = {
        (inicio + timedelta(days=i)).isoformat(): {"perguntas": 0, "custo": 0.0} for i in range(dias)
    }
    conversas: set[str] = set()
    duracoes: list[int] = []
    custo_total = 0.0
    for (func_id, conversa_id, ferramentas_json, entrada, saida, cache_leitura, cache_escrita,
         custo, duracao, criado_em) in linhas:
        custo = float(custo or 0.0)
        custo_total += custo
        totais["input_tokens"] += int(entrada or 0)
        totais["output_tokens"] += int(saida or 0)
        totais["cache_read_tokens"] += int(cache_leitura or 0)
        totais["cache_creation_tokens"] += int(cache_escrita or 0)
        if conversa_id:
            conversas.add(conversa_id)
        if duracao is not None:
            duracoes.append(int(duracao))
        try:
            nomes_ferramentas = json.loads(ferramentas_json or "[]")
        except (TypeError, ValueError):
            nomes_ferramentas = []
        if isinstance(nomes_ferramentas, list):
            ferramentas.update(str(nome) for nome in nomes_ferramentas)
        item = por_funcionario.setdefault(func_id, {"perguntas": 0, "custo": 0.0})
        item["perguntas"] += 1
        item["custo"] += custo
        dia = por_dia.get(criado_em.date().isoformat())
        if dia is not None:
            dia["perguntas"] += 1
            dia["custo"] += custo

    perguntas = len(linhas)
    return {
        "periodo_dias": dias,
        "perguntas": perguntas,
        "conversas": len(conversas),
        "funcionarios_ativos": len(por_funcionario),
        "input_tokens": totais["input_tokens"],
        "output_tokens": totais["output_tokens"],
        "cache_read_tokens": totais["cache_read_tokens"],
        "cache_creation_tokens": totais["cache_creation_tokens"],
        "custo_estimado_usd": _usd(custo_total),
        "custo_medio_por_pergunta_usd": _usd(custo_total / perguntas) if perguntas else 0.0,
        "duracao_media_ms": round(sum(duracoes) / len(duracoes)) if duracoes else 0,
        "por_funcionario": sorted(
            (
                {
                    "funcionario_id": func_id,
                    "nome": nomes.get(func_id),
                    "perguntas": dados["perguntas"],
                    "custo_estimado_usd": _usd(dados["custo"]),
                }
                for func_id, dados in por_funcionario.items()
            ),
            key=lambda item: (-item["perguntas"], -item["custo_estimado_usd"], item["funcionario_id"]),
        ),
        "ferramentas_mais_usadas": [
            {"nome": nome, "usos": usos}
            for nome, usos in sorted(ferramentas.items(), key=lambda par: (-par[1], par[0]))
        ],
        "por_dia": [
            {"data": data, "perguntas": dados["perguntas"], "custo_estimado_usd": _usd(dados["custo"])}
            for data, dados in por_dia.items()
        ],
    }


# ---------------------------------------------------------------------------
# Auditoria de acessos e retencao (v2)
# ---------------------------------------------------------------------------
def registrar_auditoria(acao: str, *, funcionario_id: int | None = None, email_informado: str | None = None,
                        recurso_tipo: str | None = None, recurso_id: str | None = None,
                        ip: str | None = None, detalhe: str | None = None) -> None:
    """
    Grava um registro em auditoria_acessos (instante = agora_utc()). Acao fora de ACOES_AUDITORIA
    -> ValueError. Textos sao cortados no tamanho da coluna (detalhe: 500 caracteres).
    """
    if acao not in ACOES_AUDITORIA:
        raise ValueError(f"Ação de auditoria inválida: {acao!r}.")
    email = _cortar(email_informado.strip() if isinstance(email_informado, str) else email_informado, 160)
    with obter_sessao() as sessao:
        sessao.add(AuditoriaAcesso(
            funcionario_id=funcionario_id,
            email_informado=email or None,
            acao=acao,
            recurso_tipo=_cortar(recurso_tipo, 40),
            recurso_id=_cortar(recurso_id, 64),
            ip=_cortar(ip, 45),
            detalhe=_cortar(detalhe, TAMANHO_DETALHE_AUDITORIA),
            criado_em=_agora(),
        ))


def listar_auditoria(funcionario_id: int | None = None, acao: str | None = None,
                     pagina: int = 1, por_pagina: int = 50) -> dict:
    """Registros de auditoria (mais recentes primeiro) no formato paginado, com funcionario_nome."""
    pagina, por_pagina = _paginacao(pagina, por_pagina, 50)
    if not _texto_valido(acao, ACOES_AUDITORIA):
        return _resultado_paginado([], pagina, por_pagina, 0)
    filtros: list[Any] = []
    if funcionario_id is not None:
        try:
            filtros.append(AuditoriaAcesso.funcionario_id == int(funcionario_id))
        except (TypeError, ValueError):
            return _resultado_paginado([], pagina, por_pagina, 0)
    if acao:
        filtros.append(AuditoriaAcesso.acao == acao)
    with obter_sessao() as sessao:
        total = sessao.scalar(select(func.count()).select_from(AuditoriaAcesso).where(*filtros)) or 0
        consulta = (
            select(AuditoriaAcesso, Funcionario.nome)
            .outerjoin(Funcionario, Funcionario.id == AuditoriaAcesso.funcionario_id)
            .where(*filtros)
            .order_by(AuditoriaAcesso.criado_em.desc(), AuditoriaAcesso.id.desc())
            .offset((pagina - 1) * por_pagina)
            .limit(por_pagina)
        )
        data = [
            {
                "id": r.id,
                "funcionario_id": r.funcionario_id,
                "funcionario_nome": nome,
                "email_informado": r.email_informado,
                "acao": r.acao,
                "recurso_tipo": r.recurso_tipo,
                "recurso_id": r.recurso_id,
                "ip": r.ip,
                "detalhe": r.detalhe,
                "criado_em": _iso(r.criado_em),
            }
            for r, nome in sessao.execute(consulta).all()
        ]
        return _resultado_paginado(data, pagina, por_pagina, total)


def contar_falhas_login(email: str, minutos: int = 15) -> int:
    """
    Quantos login_falha daquele e-mail (sem diferenciar maiusculas) aconteceram nos ultimos 'minutos'.
    Casa pelo email_informado ou pelo funcionario dono do e-mail (caso o registro so tenha o id).
    """
    email_norm = (email or "").strip().lower()
    if not email_norm:
        return 0
    corte = _agora() - timedelta(minutes=_inteiro(minutos, 15, 0))
    with obter_sessao() as sessao:
        ids_do_email = select(Funcionario.id).where(func.lower(Funcionario.email) == email_norm)
        return int(sessao.scalar(
            select(func.count())
            .select_from(AuditoriaAcesso)
            .where(
                AuditoriaAcesso.acao == "login_falha",
                AuditoriaAcesso.criado_em >= corte,
                or_(
                    func.lower(AuditoriaAcesso.email_informado) == email_norm,
                    AuditoriaAcesso.funcionario_id.in_(ids_do_email),
                ),
            )
        ) or 0)


def expurgar_dados_antigos(dias_chat: int = 180, dias_auditoria: int = 730) -> dict:
    """
    Retencao (LGPD): apaga chat_historico mais antigo que dias_chat (pelo criado_em), as conversas
    cuja ultima atualizacao e mais antiga que dias_chat (com todas as mensagens delas) e a
    auditoria mais antiga que dias_auditoria. Valores negativos ou invalidos viram o padrao/0.
    Devolve quantas linhas saíram de cada tabela: {chat_historico, chat_conversas, chat_mensagens, auditoria}.
    """
    agora = _agora()
    corte_chat = agora - timedelta(days=_inteiro(dias_chat, 180, 0))
    corte_auditoria = agora - timedelta(days=_inteiro(dias_auditoria, 730, 0))
    sem_sincronizar = {"synchronize_session": False}
    with obter_sessao() as sessao:
        conversas_antigas = select(ChatConversa.id).where(ChatConversa.atualizado_em < corte_chat)
        chat_historico = sessao.execute(
            delete(ChatHistorico).where(ChatHistorico.criado_em < corte_chat), execution_options=sem_sincronizar
        ).rowcount
        # trocas recentes que apontam para uma conversa expurgada ficam sem conversa_id
        sessao.execute(
            update(ChatHistorico).where(ChatHistorico.conversa_id.in_(conversas_antigas)).values(conversa_id=None),
            execution_options=sem_sincronizar,
        )
        chat_mensagens = sessao.execute(
            delete(ChatMensagem).where(ChatMensagem.conversa_id.in_(conversas_antigas)),
            execution_options=sem_sincronizar,
        ).rowcount
        chat_conversas = sessao.execute(
            delete(ChatConversa).where(ChatConversa.atualizado_em < corte_chat), execution_options=sem_sincronizar
        ).rowcount
        auditoria = sessao.execute(
            delete(AuditoriaAcesso).where(AuditoriaAcesso.criado_em < corte_auditoria),
            execution_options=sem_sincronizar,
        ).rowcount
        return {
            "chat_historico": int(chat_historico or 0),
            "chat_conversas": int(chat_conversas or 0),
            "chat_mensagens": int(chat_mensagens or 0),
            "auditoria": int(auditoria or 0),
        }
