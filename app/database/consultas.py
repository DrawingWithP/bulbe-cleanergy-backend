"""
Camada de Persistencia, consultas somente leitura do banco ficticio da Bulbe.

Regras (secao 1.6 do contrato):
- Cada funcao abre a propria sessao com obter_sessao().
- Devolve apenas tipos JSON-serializaveis (dict/list/str/int/float/bool/None).
  Datas viram "AAAA-MM-DD" e instantes viram "AAAA-MM-DDTHH:MM:SSZ" (UTC). Nunca objetos ORM.
- Os dados NAO sao mascarados aqui (o painel mostra completo; o chatbot mascara do lado dele).
- "Nao encontrado" ou filtro invalido: None / lista vazia (nunca levanta excecao).
- Unica escrita: registrar_chat() (auditoria do chatbot).
"""
import json
import re
import unicodedata
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.database.conexao import obter_sessao
from app.database.modelos import (
    SITUACOES_ADESAO,
    SITUACOES_CUPOM,
    SITUACOES_FATURA,
    STATUS_ATENDIMENTO,
    STATUS_CLIENTE,
    Adesao,
    Atendimento,
    Ativacao,
    Carta,
    ChatHistorico,
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
)
from app.database.seguranca import gerar_hash_senha, verificar_senha

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


# ---------------------------------------------------------------------------
# Clientes
# ---------------------------------------------------------------------------
def buscar_clientes(termo: str | None = None, status: str | None = None,
                    cidade: str | None = None, limite: int = 20) -> list[dict]:
    """
    Busca clientes. 'termo' casa (sem diferenciar maiusculas/acentos) com nome, e-mail,
    codigo de indicacao, CPF (so digitos) ou numero de instalacao. Ordenado por nome.
    """
    if not _texto_valido(status, STATUS_CLIENTE):
        return []
    limite = _limitar(limite)
    termo_norm = _normalizar(termo)
    # So compara por digitos quando o termo "parece" um documento (ex.: 123.456.789-09)
    digitos = re.sub(r"\D", "", termo or "") if termo and re.fullmatch(r"[\d.\-/\s]+", termo.strip()) else ""
    cidade_norm = _normalizar(cidade)

    with obter_sessao() as sessao:
        consulta = select(Cliente).options(selectinload(Cliente.ativacao)).order_by(Cliente.nome)
        if status:
            consulta = consulta.where(Cliente.status == status)
        resultado: list[dict] = []
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
            resultado.append({
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
            })
            if len(resultado) >= limite:
                break
        return resultado


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
    """
    with obter_sessao() as sessao:
        if sessao.get(Cliente, cliente_id) is None:
            return None
        faturas = list(sessao.scalars(select(Fatura).where(Fatura.cliente_id == cliente_id)))
        desconto = sum(f.desconto for f in faturas)
        bonus = sum(f.bonus_indicacao for f in faturas)
        return {
            "cliente_id": cliente_id,
            "meses_faturados": len(faturas),
            "economia_total_desconto": _dinheiro(desconto),
            "bonus_indicacao_total": _dinheiro(bonus),
            "economia_total": _dinheiro(desconto + bonus),
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


def listar_atendimentos(cliente_id: str | None = None, status: str | None = None,
                        limite: int = 20) -> list[dict]:
    """Atendimentos (de um cliente ou de todos), mais recentes primeiro, com o nome do cliente."""
    if not _texto_valido(status, STATUS_ATENDIMENTO):
        return []
    with obter_sessao() as sessao:
        consulta = (
            select(Atendimento, Cliente.nome)
            .join(Cliente, Cliente.id == Atendimento.cliente_id)
            .order_by(Atendimento.criado_em.desc())
            .limit(_limitar(limite))
        )
        if cliente_id is not None:
            consulta = consulta.where(Atendimento.cliente_id == cliente_id)
        if status:
            consulta = consulta.where(Atendimento.status == status)
        return [
            {
                "id": a.id,
                "cliente_id": a.cliente_id,
                "cliente_nome": nome,
                "canal": a.canal,
                "assunto": a.assunto,
                "descricao": a.descricao,
                "status": a.status,
                "criado_em": _iso(a.criado_em),
                "resolvido_em": _iso(a.resolvido_em),
            }
            for a, nome in sessao.execute(consulta).all()
        ]


def listar_adesoes(situacao: str | None = None, limite: int = 20) -> list[dict]:
    """Solicitacoes de adesao (app/site/WhatsApp), mais recentes primeiro."""
    if not _texto_valido(situacao, SITUACOES_ADESAO):
        return []
    with obter_sessao() as sessao:
        consulta = select(Adesao).order_by(Adesao.criado_em.desc()).limit(_limitar(limite))
        if situacao:
            consulta = consulta.where(Adesao.situacao == situacao)
        return [
            {
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
            for a in sessao.scalars(consulta)
        ]


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
    """Numeros gerais para a visao geral do painel."""
    agora = _agora()
    limite_30_dias = agora - timedelta(days=30)
    with obter_sessao() as sessao:
        clientes = _contar_por(sessao, Cliente.status, STATUS_CLIENTE)

        # Funil de ativacao: apenas clientes com status em_ativacao
        por_etapa = dict(
            sessao.execute(
                select(Ativacao.etapa_atual, func.count())
                .join(Cliente, Cliente.id == Ativacao.cliente_id)
                .where(Cliente.status == "em_ativacao")
                .group_by(Ativacao.etapa_atual)
            ).all()
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
            select(func.coalesce(func.sum(Fatura.desconto + Fatura.bonus_indicacao), 0.0)).select_from(Fatura)
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


def registrar_chat(funcionario_id: int, pergunta: str, resposta: str, ferramentas_usadas: list[str]) -> None:
    """Grava uma troca do chatbot (auditoria/LGPD). Unica funcao de escrita deste modulo."""
    with obter_sessao() as sessao:
        sessao.add(ChatHistorico(
            funcionario_id=funcionario_id,
            pergunta=pergunta,
            resposta=resposta,
            ferramentas_usadas=json.dumps(list(ferramentas_usadas or []), ensure_ascii=False),
        ))
