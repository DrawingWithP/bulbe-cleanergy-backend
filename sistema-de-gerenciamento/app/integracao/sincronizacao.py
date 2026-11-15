"""
Sincronizacao app -> painel.

Le o banco do app (backend/, somente leitura) e espelha no banco do painel os dados que o
app cria e altera: usinas, parceiros, dicas, clientes, ativacoes, Clube (ofensiva, cartas e
cupons), indicacoes, simulacoes e adesoes. O app e a fonte da verdade desses dados; o painel
continua dono do que so ele tem (funcionarios, faturas, notificacoes, atendimentos, chat e
auditoria).

Regras
- Cada linha espelhada guarda o id do app em `id_app`.
- Vinculo: se o painel ja tem o mesmo registro (cliente com o mesmo CPF ou e-mail; parceiro,
  usina ou dica com o mesmo nome/titulo), a linha ficticia e vinculada ao app em vez de
  duplicada (`importado_do_app=False`). Ao vincular um cliente, a ativacao e o Clube (cartas e
  cupons) ficticios dele dao lugar aos do app, que e o que o cliente ve na tela. Faturas,
  notificacoes, atendimentos e o historico de indicacoes/simulacoes ficticio continuam.
- Linha nova: criada com `importado_do_app=True` (UUIDs do app sao mantidos como id).
- Registro removido no app: linha importada e apagada; linha vinculada so perde o vinculo.
- Mudanca de etapa de ativacao vira um evento em ativacao_eventos (alimenta "clientes parados").
- Tudo numa transacao: se algo falhar, o banco do painel fica como estava.
"""
from __future__ import annotations

import json
import logging
import re
import sqlite3
import threading
import time
import unicodedata
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Iterable
from urllib.parse import unquote

from sqlalchemy import create_engine, delete, func, inspect, select, text, update
from sqlalchemy.engine import Connection, Engine, make_url
from sqlalchemy.orm import Session

from app.database.conexao import obter_sessao
from app.database.modelos import (
    SITUACOES_ADESAO,
    SITUACOES_CARTA,
    SITUACOES_CUPOM,
    SITUACOES_INDICACAO,
    STATUS_CLIENTE,
    STATUS_USINA,
    TIPOS_CARTA,
    Adesao,
    Atendimento,
    Ativacao,
    AtivacaoEvento,
    Carta,
    Cliente,
    ClubeStatus,
    Cupom,
    Dica,
    Fatura,
    Indicacao,
    Notificacao,
    Parceiro,
    Simulacao,
    Usina,
)
from app.integracao.config import ConfigIntegracao, obter_config

logger = logging.getLogger(__name__)

TABELAS_APP = (
    "usinas", "parceiros", "dicas", "clientes", "ativacoes", "ofensivas_clube",
    "cartas", "cupons", "indicacoes", "simulacoes", "adesoes",
)
BONUS_INDICACAO = 50.0
DESCONTO_PADRAO = 0.15
META_SEQUENCIA = 5

_trava = threading.Lock()
_engines: dict[str, Engine] = {}
_estado: dict[str, Any] = {
    "ultima_execucao": None,
    "sucesso": None,
    "erro": None,
    "duracao_ms": None,
    "contagens": {},
    "avisos": [],
}


class IntegracaoIndisponivel(Exception):
    """A integracao esta desligada ou o banco do app nao pode ser lido."""


# ---------------------------------------------------------------------------
# Conversoes
# ---------------------------------------------------------------------------
def _agora() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)


def _digitos(valor: Any) -> str:
    return re.sub(r"\D", "", str(valor or ""))


def _normalizar(texto: Any) -> str:
    base = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", base).strip().lower()


def _cortar(texto: Any, tamanho: int) -> str:
    return str(texto or "").strip()[:tamanho]


def _instante(valor: Any) -> datetime | None:
    """ISO (com ou sem 'Z'/fuso), date ou datetime -> datetime UTC sem tzinfo."""
    if valor is None or valor == "":
        return None
    if isinstance(valor, datetime):
        dt = valor
    elif isinstance(valor, date):
        dt = datetime(valor.year, valor.month, valor.day, 12, 0)
    else:
        bruto = str(valor).strip().replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(bruto)
        except ValueError:
            try:
                d = date.fromisoformat(bruto[:10])
            except ValueError:
                return None
            dt = datetime(d.year, d.month, d.day, 12, 0)
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt.replace(microsecond=0)


def _data(valor: Any) -> date | None:
    instante = _instante(valor)
    return instante.date() if instante else None


def _bool(valor: Any) -> bool:
    if isinstance(valor, str):
        return valor.strip().lower() in {"1", "true", "t", "sim"}
    return bool(valor)


def _numero(valor: Any, padrao: float = 0.0) -> float:
    try:
        return float(valor)
    except (TypeError, ValueError):
        return padrao


def _valor_em(valor: Any, permitidos: tuple[str, ...], padrao: str) -> str:
    texto = str(valor or "").strip().lower()
    return texto if texto in permitidos else padrao


# ---------------------------------------------------------------------------
# Leitura do banco do app (somente leitura)
# ---------------------------------------------------------------------------
def _engine_app(url: str) -> Engine:
    """Engine do banco do app. SQLite abre em modo somente leitura (mode=ro)."""
    if url in _engines:
        return _engines[url]

    url_obj = make_url(url)
    if url_obj.get_backend_name() == "sqlite":
        banco = url_obj.database or ""
        if not banco or banco == ":memory:":
            raise IntegracaoIndisponivel("INTEGRACAO_APP_DB_URL precisa apontar para um arquivo SQLite.")
        caminho = Path(unquote(banco))
        if not caminho.is_absolute():
            caminho = (Path.cwd() / caminho).resolve()
        if not caminho.exists():
            raise IntegracaoIndisponivel(f"Banco do app nao encontrado: {caminho}")
        uri = caminho.as_uri() + "?mode=ro"

        def conectar() -> sqlite3.Connection:
            return sqlite3.connect(uri, uri=True, check_same_thread=False)

        engine = create_engine("sqlite://", creator=conectar)
    else:
        engine = create_engine(url, pool_pre_ping=True)

    _engines[url] = engine
    return engine


def descartar_conexoes() -> None:
    """Fecha os engines do banco do app (usado nos testes e ao trocar a URL)."""
    for engine in _engines.values():
        engine.dispose()
    _engines.clear()


def _ler_app(conexao: Connection) -> dict[str, list[dict]]:
    existentes = set(inspect(conexao).get_table_names())
    if "clientes" not in existentes:
        raise IntegracaoIndisponivel(
            "O banco do app nao tem as tabelas do backend. Rode 'alembic upgrade head' na pasta backend/."
        )
    dados: dict[str, list[dict]] = {}
    for tabela in TABELAS_APP:  # nomes fixos (sem entrada do usuario)
        if tabela in existentes:
            dados[tabela] = [dict(linha) for linha in conexao.execute(text(f'SELECT * FROM "{tabela}"')).mappings()]
        else:
            dados[tabela] = []
    return dados


# ---------------------------------------------------------------------------
# Contexto da sincronizacao
# ---------------------------------------------------------------------------
@dataclass
class _Contagem:
    criados: int = 0
    atualizados: int = 0
    vinculados: int = 0
    removidos: int = 0
    ignorados: int = 0

    def como_dict(self) -> dict[str, int]:
        return dict(self.__dict__)


@dataclass
class _Contexto:
    sessao: Session
    clientes: dict[str, str] = field(default_factory=dict)   # id no app -> id no painel
    parceiros: dict[str, str] = field(default_factory=dict)
    usinas: dict[str, int] = field(default_factory=dict)
    cartas: dict[str, str] = field(default_factory=dict)
    cupons: dict[str, str] = field(default_factory=dict)
    contagens: dict[str, _Contagem] = field(default_factory=dict)
    avisos: list[str] = field(default_factory=list)

    def contagem(self, nome: str) -> _Contagem:
        return self.contagens.setdefault(nome, _Contagem())

    def avisar(self, mensagem: str) -> None:
        if len(self.avisos) < 50:
            self.avisos.append(mensagem)
        logger.warning("Integracao com o app: %s", mensagem)


def _vincular(
    ctx: _Contexto,
    modelo: type,
    nome: str,
    id_app: str,
    equivalente: Callable[[], Any] | None,
    criar: Callable[[], Any],
) -> tuple[Any, bool, bool]:
    """
    Linha do painel para o registro do app: ja vinculada, uma equivalente ficticia (vincula) ou nova.
    Devolve (linha, criada, vinculada_agora).
    """
    sessao = ctx.sessao
    linha = sessao.scalar(select(modelo).where(modelo.id_app == id_app).limit(1))
    if linha is not None:
        ctx.contagem(nome).atualizados += 1
        return linha, False, False

    if equivalente is not None:
        linha = equivalente()
        if linha is not None:
            linha.id_app = id_app
            linha.importado_do_app = False
            ctx.contagem(nome).vinculados += 1
            return linha, False, True

    linha = criar()
    linha.id_app = id_app
    linha.importado_do_app = True
    sessao.add(linha)
    ctx.contagem(nome).criados += 1
    return linha, True, False


def _sem_vinculo(modelo: type) -> Any:
    return modelo.id_app.is_(None)


def _remover_ausentes(
    ctx: _Contexto,
    modelo: type,
    nome: str,
    ids_app: Iterable[str],
    apagar: Callable[[Any], None] | None = None,
) -> None:
    """Registros que sumiram do app: importados sao apagados; vinculados perdem o vinculo."""
    presentes = set(ids_app)
    linhas = ctx.sessao.scalars(select(modelo).where(modelo.id_app.is_not(None))).all()
    for linha in linhas:
        if linha.id_app in presentes:
            continue
        if linha.importado_do_app:
            if apagar is not None:
                apagar(linha)
            else:
                ctx.sessao.delete(linha)
            ctx.contagem(nome).removidos += 1
        else:
            linha.id_app = None
    ctx.sessao.flush()


def _id_livre(sessao: Session, modelo: type, candidato: Any) -> str:
    """Usa o id do app quando ele ainda nao existe no painel; senao, um UUID novo."""
    if candidato and sessao.get(modelo, str(candidato)) is None:
        return str(candidato)
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Catalogos: usinas, parceiros e dicas
# ---------------------------------------------------------------------------
def _sinc_usinas(ctx: _Contexto, linhas: list[dict]) -> None:
    sessao = ctx.sessao
    for app in linhas:
        id_app = str(app["id"])
        capacidade = _numero(app.get("capacidade_geracao_kwh"))
        if capacidade <= 0 or not app.get("nome"):
            ctx.contagem("usinas").ignorados += 1
            continue
        nome_norm = _normalizar(app["nome"])
        linha, _, _ = _vincular(
            ctx, Usina, "usinas", id_app,
            lambda: next((u for u in sessao.scalars(select(Usina).where(_sem_vinculo(Usina)))
                          if _normalizar(u.nome) == nome_norm), None),
            lambda: Usina(),
        )
        linha.nome = _cortar(app["nome"], 100)
        linha.localizacao = _cortar(app.get("localizacao"), 100) or "-"
        linha.capacidade_geracao_kwh = capacidade
        linha.status = _valor_em(app.get("status"), STATUS_USINA, "ativa")
        linha.data_ativacao = _data(app.get("data_ativacao")) or _agora().date()
        sessao.flush()
        ctx.usinas[id_app] = linha.id

    def apagar(usina: Usina) -> None:
        sessao.execute(update(Cliente).where(Cliente.usina_id == usina.id).values(usina_id=None))
        sessao.delete(usina)

    _remover_ausentes(ctx, Usina, "usinas", (str(a["id"]) for a in linhas), apagar)


def _sinc_parceiros(ctx: _Contexto, linhas: list[dict]) -> None:
    sessao = ctx.sessao
    for app in linhas:
        id_app = str(app["id"])
        nome = _cortar(app.get("nome"), 100)
        if not nome:
            ctx.contagem("parceiros").ignorados += 1
            continue
        nome_norm = _normalizar(nome)
        linha, criada, _ = _vincular(
            ctx, Parceiro, "parceiros", id_app,
            lambda: next((p for p in sessao.scalars(select(Parceiro).where(_sem_vinculo(Parceiro)))
                          if _normalizar(p.nome) == nome_norm), None),
            lambda: Parceiro(id=_id_livre(sessao, Parceiro, id_app), criado_em=_instante(app.get("criado_em")) or _agora()),
        )
        # nome e unico no painel: se outro parceiro ja usa o nome, mantem o atual
        ocupado = sessao.scalar(select(Parceiro.id).where(Parceiro.nome == nome, Parceiro.id != linha.id).limit(1))
        if ocupado is None:
            linha.nome = nome
        elif criada:
            linha.nome = _cortar(f"{nome} (app)", 100)
        linha.categoria = _cortar(app.get("categoria"), 60) or "Outros"
        # A logo do painel (asset local) e mantida; o app usa uma URL de CDN.
        if criada or not linha.logo_url:
            linha.logo_url = _cortar(app.get("logo_url"), 255) or None
        linha.ativo = _bool(app.get("ativo", True))
        sessao.flush()
        ctx.parceiros[id_app] = linha.id

    def apagar(parceiro: Parceiro) -> None:
        sessao.execute(update(Cupom).where(Cupom.parceiro_id == parceiro.id).values(parceiro_id=None))
        sessao.delete(parceiro)

    _remover_ausentes(ctx, Parceiro, "parceiros", (str(a["id"]) for a in linhas), apagar)


def _sinc_dicas(ctx: _Contexto, linhas: list[dict]) -> None:
    sessao = ctx.sessao
    for app in linhas:
        id_app = str(app["id"])
        titulo = _cortar(app.get("titulo"), 100)
        if not titulo:
            ctx.contagem("dicas").ignorados += 1
            continue
        titulo_norm = _normalizar(titulo)

        def nova() -> Dica:
            ordem = (sessao.scalar(select(func.max(Dica.ordem))) or 0) + 1
            return Dica(ordem=ordem)

        linha, _, _ = _vincular(
            ctx, Dica, "dicas", id_app,
            lambda: next((d for d in sessao.scalars(select(Dica).where(_sem_vinculo(Dica)))
                          if _normalizar(d.titulo) == titulo_norm), None),
            nova,
        )
        economia = round(_numero(app.get("economia")), 2)
        linha.titulo = titulo
        linha.descricao = _cortar(app.get("descricao"), 250)
        linha.economia_mensal = economia
        linha.economia_anual = round(economia * 12, 2)
        sessao.flush()

    _remover_ausentes(ctx, Dica, "dicas", (str(a["id"]) for a in linhas))


# ---------------------------------------------------------------------------
# Clientes e ativacao
# ---------------------------------------------------------------------------
def _codigo_indicacao(sessao: Session, nome: str, id_app: str) -> str:
    primeiro = re.sub(r"[^A-Z]", "", _normalizar(nome).split(" ")[0].upper())[:10] or "CLIENTE"
    base = f"{primeiro}{_digitos(id_app)[:4] or '0000'}"
    codigo, n = base, 1
    while sessao.scalar(select(Cliente.id).where(Cliente.codigo_indicacao == codigo).limit(1)) is not None:
        n += 1
        codigo = f"{base}{n}"
    return codigo[:30]


def _limpar_clube_ficticio(sessao: Session, cliente_id: str) -> None:
    """Ao vincular um cliente ao app, o Clube passa a ser o do app (o que o cliente ve na tela)."""
    sessao.execute(
        update(Carta).where(Carta.cliente_id == cliente_id, _sem_vinculo(Carta)).values(cupom_id=None)
    )
    sessao.execute(delete(Cupom).where(Cupom.cliente_id == cliente_id, _sem_vinculo(Cupom)))
    sessao.execute(delete(Carta).where(Carta.cliente_id == cliente_id, _sem_vinculo(Carta)))
    sessao.execute(delete(ClubeStatus).where(ClubeStatus.cliente_id == cliente_id))
    sessao.flush()


def _apagar_cliente_importado(sessao: Session, cliente: Cliente) -> None:
    cid = cliente.id
    sessao.execute(update(Carta).where(Carta.cliente_id == cid).values(cupom_id=None))
    for modelo in (Cupom, Carta, ClubeStatus, AtivacaoEvento, Ativacao, Indicacao, Fatura, Notificacao, Atendimento):
        sessao.execute(delete(modelo).where(modelo.cliente_id == cid))
    for modelo in (Simulacao, Adesao):
        sessao.execute(update(modelo).where(modelo.cliente_id == cid).values(cliente_id=None))
    sessao.delete(cliente)


def _sinc_clientes(ctx: _Contexto, linhas: list[dict]) -> None:
    sessao = ctx.sessao
    for app in linhas:
        id_app = str(app["id"])
        cpf = _digitos(app.get("cpf"))
        email = _cortar(app.get("email"), 160).lower()
        if len(cpf) != 11 or not app.get("nome"):
            ctx.contagem("clientes").ignorados += 1
            ctx.avisar(f"cliente {id_app} ignorado: CPF ou nome invalido")
            continue

        def equivalente() -> Cliente | None:
            por_cpf = sessao.scalar(select(Cliente).where(Cliente.cpf == cpf, _sem_vinculo(Cliente)).limit(1))
            if por_cpf is not None:
                return por_cpf
            if email:
                return sessao.scalar(
                    select(Cliente).where(func.lower(Cliente.email) == email, _sem_vinculo(Cliente)).limit(1)
                )
            return None

        criado_em = _instante(app.get("criado_em")) or _agora()
        linha, criada, vinculada = _vincular(
            ctx, Cliente, "clientes", id_app, equivalente,
            lambda: Cliente(
                id=_id_livre(sessao, Cliente, id_app),
                tipo="residencia",
                codigo_indicacao=_codigo_indicacao(sessao, str(app["nome"]), id_app),
                criado_em=criado_em,
            ),
        )
        if vinculada:
            _limpar_clube_ficticio(sessao, linha.id)

        # CPF e numero de instalacao sao unicos no painel: so troca se o valor estiver livre.
        cpf_ocupado = sessao.scalar(select(Cliente.id).where(Cliente.cpf == cpf, Cliente.id != linha.id).limit(1))
        if cpf_ocupado is None:
            linha.cpf = cpf
        elif criada:
            sessao.expunge(linha)
            ctx.contagem("clientes").criados -= 1
            ctx.contagem("clientes").ignorados += 1
            ctx.avisar(f"cliente {id_app} ignorado: CPF ja usado por outro cliente do painel")
            continue
        instalacao = _cortar(app.get("numero_instalacao"), 20) or f"APP{_digitos(id_app)[:12]}"
        inst_ocupada = sessao.scalar(
            select(Cliente.id).where(Cliente.numero_instalacao == instalacao, Cliente.id != linha.id).limit(1)
        )
        if inst_ocupada is None:
            linha.numero_instalacao = instalacao
        elif criada:
            linha.numero_instalacao = f"APP{uuid.uuid4().hex[:12]}"

        linha.nome = _cortar(app["nome"], 120)
        linha.email = email or linha.email or ""
        linha.telefone = _digitos(app.get("telefone"))[-11:] or linha.telefone or ""
        linha.cep = _digitos(app.get("cep"))[:8] or linha.cep or ""
        linha.logradouro = _cortar(app.get("logradouro"), 120)
        linha.numero = _cortar(app.get("numero"), 10)
        linha.complemento = _cortar(app.get("complemento"), 60) or None
        linha.bairro = _cortar(app.get("bairro"), 80)
        linha.cidade = _cortar(app.get("cidade"), 80)
        uf = _cortar(app.get("uf"), 2).upper()
        linha.uf = uf if len(uf) == 2 else (linha.uf or "MG")
        linha.distribuidora = _cortar(app.get("distribuidora"), 40) or "CEMIG"
        linha.status = _valor_em(app.get("status"), STATUS_CLIENTE, "em_ativacao")
        linha.app_acesso_habilitado = _bool(app.get("acesso_habilitado"))
        sessao.flush()
        ctx.clientes[id_app] = linha.id

    _remover_ausentes(
        ctx, Cliente, "clientes", (str(a["id"]) for a in linhas),
        lambda cliente: _apagar_cliente_importado(sessao, cliente),
    )


def _observacoes(valor: Any) -> list[str]:
    if isinstance(valor, list):
        itens = valor
    else:
        try:
            itens = json.loads(valor or "[]")
        except (TypeError, ValueError):
            itens = []
    return [str(item).strip() for item in itens if str(item or "").strip()]


def _sinc_ativacoes(ctx: _Contexto, linhas: list[dict]) -> None:
    sessao = ctx.sessao
    vistos: set[str] = set()
    for app in linhas:
        cliente_id = ctx.clientes.get(str(app.get("cliente_id")))
        if cliente_id is None:
            continue
        vistos.add(cliente_id)
        etapa = min(max(int(_numero(app.get("etapa_atual"), 1)), 1), 5)
        atualizado = _instante(app.get("atualizado_em")) or _agora()
        previsao = _data(app.get("previsao_conclusao")) or (atualizado.date() + timedelta(days=90))

        ativacao = sessao.get(Ativacao, cliente_id)
        contagem = ctx.contagem("ativacoes")
        if ativacao is None:
            ativacao = Ativacao(cliente_id=cliente_id, etapa_atual=etapa, previsao_conclusao=previsao,
                                atualizado_em=atualizado)
            sessao.add(ativacao)
            contagem.criados += 1
            mudou = True
        else:
            mudou = ativacao.etapa_atual != etapa
            contagem.atualizados += 1
        if mudou:
            sessao.add(AtivacaoEvento(
                cliente_id=cliente_id, etapa=etapa,
                observacao=f"Etapa {etapa} registrada no app.", ocorrido_em=atualizado,
            ))
        ativacao.etapa_atual = etapa
        ativacao.previsao_conclusao = previsao
        ativacao.atualizado_em = atualizado

        ja_registradas = set(sessao.scalars(
            select(AtivacaoEvento.observacao).where(AtivacaoEvento.cliente_id == cliente_id)
        ))
        for observacao in _observacoes(app.get("observacoes")):
            texto = _cortar(observacao, 500)
            if texto not in ja_registradas:
                sessao.add(AtivacaoEvento(cliente_id=cliente_id, etapa=etapa, observacao=texto,
                                          ocorrido_em=atualizado))
                ja_registradas.add(texto)
    sessao.flush()


# ---------------------------------------------------------------------------
# Clube: cartas, cupons e ofensiva
# ---------------------------------------------------------------------------
def _sinc_cartas(ctx: _Contexto, linhas: list[dict]) -> None:
    sessao = ctx.sessao
    validos: list[str] = []
    for app in linhas:
        id_app = str(app["id"])
        cliente_id = ctx.clientes.get(str(app.get("cliente_id")))
        disponivel_em = _instante(app.get("disponivel_em"))
        if cliente_id is None or disponivel_em is None:
            ctx.contagem("cartas").ignorados += 1
            continue
        semana = int(_numero(app.get("semana"), 1))
        conflito = sessao.scalar(
            select(Carta).where(Carta.cliente_id == cliente_id, Carta.semana == semana,
                                (Carta.id_app.is_(None)) | (Carta.id_app != id_app)).limit(1)
        )
        if conflito is not None:
            ctx.contagem("cartas").ignorados += 1
            ctx.avisar(f"carta {id_app} ignorada: o cliente ja tem uma carta na semana {semana}")
            continue
        linha, _, _ = _vincular(ctx, Carta, "cartas", id_app, None,
                                lambda: Carta(id=_id_livre(sessao, Carta, id_app)))
        linha.cliente_id = cliente_id
        linha.semana = semana
        linha.tipo = _valor_em(app.get("tipo"), TIPOS_CARTA, "normal")
        # "bloqueada" (carta futura) nao existe no painel: fica disponivel com data futura.
        linha.situacao = _valor_em(app.get("situacao"), SITUACOES_CARTA, "disponivel")
        linha.disponivel_em = disponivel_em
        linha.aberta_em = _instante(app.get("aberta_em"))
        sessao.flush()
        ctx.cartas[id_app] = linha.id
        validos.append(id_app)

    def apagar(carta: Carta) -> None:
        sessao.execute(update(Cupom).where(Cupom.carta_id == carta.id).values(carta_id=None))
        carta.cupom_id = None
        sessao.flush()
        sessao.delete(carta)

    _remover_ausentes(ctx, Carta, "cartas", validos, apagar)


def _sinc_cupons(ctx: _Contexto, linhas: list[dict], cartas_app: list[dict]) -> None:
    sessao = ctx.sessao
    validos: list[str] = []
    parceiros_por_nome = {_normalizar(p.nome): p.id for p in sessao.scalars(select(Parceiro))}
    for app in linhas:
        id_app = str(app["id"])
        cliente_id = ctx.clientes.get(str(app.get("cliente_id")))
        valido_ate = _data(app.get("valido_ate"))
        if cliente_id is None or valido_ate is None:
            ctx.contagem("cupons").ignorados += 1
            continue
        linha, _, _ = _vincular(ctx, Cupom, "cupons", id_app, None,
                                lambda: Cupom(id=_id_livre(sessao, Cupom, id_app)))
        linha.cliente_id = cliente_id
        linha.carta_id = ctx.cartas.get(str(app.get("carta_id"))) if app.get("carta_id") else None
        linha.parceiro_id = (
            ctx.parceiros.get(str(app.get("parceiro_id")))
            or parceiros_por_nome.get(_normalizar(app.get("parceiro_nome")))
        )
        linha.titulo = _cortar(app.get("titulo"), 120) or "Cupom do Clube Bulbe"
        linha.descricao = _cortar(app.get("descricao"), 300)
        linha.codigo = _cortar(app.get("codigo"), 30) or None
        linha.situacao = _valor_em(app.get("situacao"), SITUACOES_CUPOM, "ativo")
        linha.aberto_em = _instante(app.get("criado_em")) or _agora()
        linha.valido_ate = valido_ate
        linha.usado_em = _instante(app.get("usado_em"))
        sessao.flush()
        ctx.cupons[id_app] = linha.id
        validos.append(id_app)

    _remover_ausentes(ctx, Cupom, "cupons", validos)

    # cartas.cupom_id (o app guarda o vinculo nos dois sentidos)
    for app in cartas_app:
        carta_id = ctx.cartas.get(str(app["id"]))
        if carta_id is None:
            continue
        carta = sessao.get(Carta, carta_id)
        if carta is not None:
            carta.cupom_id = ctx.cupons.get(str(app.get("cupom_id"))) if app.get("cupom_id") else None
    sessao.flush()


def _sinc_clube(ctx: _Contexto, ofensivas: list[dict], cartas_app: list[dict]) -> None:
    sessao = ctx.sessao
    agora = _agora()
    sequencia = {str(o.get("cliente_id")): int(_numero(o.get("semanas_sequencia"))) for o in ofensivas}
    cartas_por_cliente: dict[str, list[dict]] = {}
    for carta in cartas_app:
        cartas_por_cliente.setdefault(str(carta.get("cliente_id")), []).append(carta)

    for id_app_cliente, cliente_id in ctx.clientes.items():
        cartas = cartas_por_cliente.get(id_app_cliente, [])
        if id_app_cliente not in sequencia and not cartas:
            continue
        nao_abertas = [c for c in cartas if str(c.get("situacao")) in {"disponivel", "bloqueada"}]
        futuras = [d for d in (_instante(c.get("disponivel_em")) for c in nao_abertas) if d and d > agora]
        status = sessao.get(ClubeStatus, cliente_id)
        if status is None:
            status = ClubeStatus(cliente_id=cliente_id)
            sessao.add(status)
            ctx.contagem("clube").criados += 1
        else:
            ctx.contagem("clube").atualizados += 1
        status.semanas_sequencia = min(max(sequencia.get(id_app_cliente, 0), 0), META_SEQUENCIA)
        status.meta_sequencia = META_SEQUENCIA
        status.proxima_carta_em = min(futuras) if futuras else None
        status.bonus_especial_pendente = any(
            str(c.get("tipo")) == "especial" and str(c.get("situacao")) == "disponivel" for c in cartas
        )
        status.atualizado_em = agora
    sessao.flush()


# ---------------------------------------------------------------------------
# Indicacoes, simulacoes e adesoes
# ---------------------------------------------------------------------------
_SITUACAO_INDICACAO = {"cancelada": "expirada"}


def _sinc_indicacoes(ctx: _Contexto, linhas: list[dict]) -> None:
    sessao = ctx.sessao
    validos: list[str] = []
    for app in linhas:
        id_app = str(app["id"])
        cliente_id = ctx.clientes.get(str(app.get("cliente_id")))
        if cliente_id is None:
            ctx.contagem("indicacoes").ignorados += 1
            continue
        contato = _cortar(app.get("contato"), 160)
        linha, _, _ = _vincular(ctx, Indicacao, "indicacoes", id_app, None,
                                lambda: Indicacao(id=str(uuid.uuid4()), criado_em=_agora()))
        situacao = str(app.get("situacao") or "pendente").lower()
        linha.cliente_id = cliente_id
        linha.nome_indicado = _cortar(app.get("nome"), 120)
        linha.contato_indicado = contato
        linha.canal = "email" if "@" in contato else "whatsapp"
        linha.situacao = _valor_em(_SITUACAO_INDICACAO.get(situacao, situacao), SITUACOES_INDICACAO, "pendente")
        linha.bonus = max(_numero(app.get("bonus"), BONUS_INDICACAO), 0.0)
        if linha.situacao == "aderiu" and linha.creditado_em is None:
            linha.creditado_em = _agora().date()
        sessao.flush()
        validos.append(id_app)

    _remover_ausentes(ctx, Indicacao, "indicacoes", validos)


def _sinc_simulacoes(ctx: _Contexto, linhas: list[dict]) -> None:
    sessao = ctx.sessao
    validos: list[str] = []
    for app in linhas:
        id_app = str(app["id"])
        valor = _numero(app.get("valor_atual"))
        meses = int(_numero(app.get("periodo_meses")))
        amigos = max(int(_numero(app.get("indicacoes"))), 0)
        if valor <= 0 or not 1 <= meses <= 60:
            ctx.contagem("simulacoes").ignorados += 1
            continue
        cliente_id = ctx.clientes.get(str(app.get("cliente_id"))) if app.get("cliente_id") else None
        economia = app.get("economia_total")
        if economia is None:
            desconto = max(valor - _numero(app.get("valor_proposto"), valor * (1 - DESCONTO_PADRAO)), 0.0)
            economia = desconto * meses + amigos * BONUS_INDICACAO
        linha, _, _ = _vincular(ctx, Simulacao, "simulacoes", id_app, None, lambda: Simulacao())
        linha.origem = "cliente" if cliente_id else "visitante"
        linha.cliente_id = cliente_id
        linha.valor_conta = round(valor, 2)
        linha.meses = meses
        linha.amigos_indicados = amigos
        linha.economia_total = round(_numero(economia), 2)
        linha.criado_em = _instante(app.get("data_ativacao")) or _agora()
        sessao.flush()
        validos.append(id_app)

    _remover_ausentes(ctx, Simulacao, "simulacoes", validos)


def _sinc_adesoes(ctx: _Contexto, linhas: list[dict]) -> None:
    sessao = ctx.sessao
    validos: list[str] = []
    for app in linhas:
        id_app = str(app["id"])
        cpf = _digitos(app.get("cpf"))
        linha, _, _ = _vincular(ctx, Adesao, "adesoes", id_app, None,
                                lambda: Adesao(id=str(uuid.uuid4()), origem="app"))
        valor = _numero(app.get("valor_conta_atual")) or None
        linha.nome = _cortar(app.get("nome"), 120)
        linha.email = _cortar(app.get("email"), 160)
        linha.cpf = cpf if len(cpf) == 11 else None
        linha.telefone = _digitos(app.get("telefone"))[-11:] or None
        linha.cidade = _cortar(app.get("cidade"), 80) or None
        uf = _cortar(app.get("uf"), 2).upper()
        linha.uf = uf if len(uf) == 2 else None
        linha.distribuidora = _cortar(app.get("distribuidora"), 40) or None
        linha.numero_instalacao = _cortar(app.get("numero_instalacao"), 20) or None
        linha.valor_conta_atual = valor
        linha.economia_mensal_estimada = round(valor * DESCONTO_PADRAO, 2) if valor else None
        linha.situacao = _valor_em(app.get("status"), SITUACOES_ADESAO, "enviada")
        linha.cliente_id = (
            sessao.scalar(select(Cliente.id).where(Cliente.cpf == cpf).limit(1)) if linha.cpf else None
        )
        linha.criado_em = _instante(app.get("data_ativacao")) or linha.criado_em or _agora()
        sessao.flush()
        validos.append(id_app)

    _remover_ausentes(ctx, Adesao, "adesoes", validos)


# ---------------------------------------------------------------------------
# API publica do modulo
# ---------------------------------------------------------------------------
def _aplicar(sessao: Session, dados: dict[str, list[dict]]) -> _Contexto:
    ctx = _Contexto(sessao=sessao)
    # Sem autoflush: uma consulta no meio do preenchimento nao grava linha incompleta.
    # Cada registro termina com um flush explicito.
    with sessao.no_autoflush:
        _sinc_usinas(ctx, dados["usinas"])
        _sinc_parceiros(ctx, dados["parceiros"])
        _sinc_dicas(ctx, dados["dicas"])
        _sinc_clientes(ctx, dados["clientes"])
        _sinc_ativacoes(ctx, dados["ativacoes"])
        _sinc_cartas(ctx, dados["cartas"])
        _sinc_cupons(ctx, dados["cupons"], dados["cartas"])
        _sinc_clube(ctx, dados["ofensivas_clube"], dados["cartas"])
        _sinc_indicacoes(ctx, dados["indicacoes"])
        _sinc_simulacoes(ctx, dados["simulacoes"])
        _sinc_adesoes(ctx, dados["adesoes"])
    return ctx


def sincronizar(config: ConfigIntegracao | None = None) -> dict:
    """
    Executa uma sincronizacao completa (app -> painel) e devolve o estado.
    Levanta IntegracaoIndisponivel se a integracao estiver desligada ou o banco do app nao puder ser lido.
    """
    cfg = config or obter_config()
    if not cfg.ativa:
        raise IntegracaoIndisponivel(cfg.motivo_desligada or "Integracao desligada.")

    with _trava:
        inicio = time.perf_counter()
        try:
            with _engine_app(cfg.url_banco_app).connect() as conexao:
                dados = _ler_app(conexao)
            with obter_sessao() as sessao:
                ctx = _aplicar(sessao, dados)
            _estado.update(
                sucesso=True, erro=None,
                contagens={nome: c.como_dict() for nome, c in ctx.contagens.items()},
                avisos=ctx.avisos,
            )
        except Exception as erro:  # noqa: BLE001 - o estado guarda o erro para a tela de admin
            _estado.update(sucesso=False, erro=str(erro)[:500], avisos=[])
            raise
        finally:
            _estado["ultima_execucao"] = _agora().isoformat()
            _estado["duracao_ms"] = int((time.perf_counter() - inicio) * 1000)
        return estado()


def sincronizar_sem_erro() -> dict | None:
    """Versao para o agendador: nunca levanta (o erro fica no estado e no log)."""
    try:
        return sincronizar()
    except IntegracaoIndisponivel as erro:
        logger.info("Integracao com o app indisponivel: %s", erro)
    except Exception:  # noqa: BLE001
        logger.exception("Falha na sincronizacao com o app.")
    return None


def estado() -> dict:
    """Configuracao (sem segredos) e resultado da ultima sincronizacao."""
    cfg = obter_config()
    return {
        "ativa": cfg.ativa,
        "motivo": cfg.motivo_desligada,
        "banco_app": _descrever_url(cfg.url_banco_app),
        "intervalo_segundos": cfg.intervalo_segundos,
        "api_app": cfg.api_url,
        "ultima_execucao": _estado["ultima_execucao"],
        "sucesso": _estado["sucesso"],
        "erro": _estado["erro"],
        "duracao_ms": _estado["duracao_ms"],
        "contagens": _estado["contagens"],
        "avisos": _estado["avisos"],
    }


def _descrever_url(url: str | None) -> str | None:
    """URL do banco sem senha (para exibir no painel)."""
    if not url:
        return None
    try:
        return make_url(url).render_as_string(hide_password=True)
    except Exception:  # noqa: BLE001
        return "(url invalida)"


def reiniciar_estado() -> None:
    """Limpa o estado em memoria (testes)."""
    _estado.update(ultima_execucao=None, sucesso=None, erro=None, duracao_ms=None, contagens={}, avisos=[])
