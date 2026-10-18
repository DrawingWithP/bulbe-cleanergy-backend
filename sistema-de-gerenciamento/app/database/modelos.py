"""
Camada de Persistencia, modelos ORM (SQLAlchemy 2) do banco ficticio da Bulbe.

20 tabelas: funcionarios, usinas, clientes, adesoes, ativacoes, ativacao_eventos, faturas,
indicacoes, parceiros, clube_status, cartas, cupons, dicas, simulacoes, notificacoes,
atendimentos, chat_historico, chat_conversas, chat_mensagens e auditoria_acessos
(as 3 ultimas entraram na v2 do sistema de gerenciamento).

Convencoes:
- IDs de cliente, adesao, carta, cupom, indicacao e parceiro: UUID v4 em string (36 chars).
  Demais tabelas: inteiro autoincremento.
- Datas em date/datetime UTC "ingenuo" (sem tzinfo). Valores monetarios em float (2 casas).
- Os "enums" sao String + CHECK constraint (funciona igual no SQLite e em outros bancos).
"""
import uuid
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.conexao import Base

# ---------------------------------------------------------------------------
# Valores validos (usados nas CHECK constraints e na validacao das consultas)
# ---------------------------------------------------------------------------
PERFIS_FUNCIONARIO = ("atendimento", "admin")
STATUS_USINA = ("ativa", "em_manutencao", "inativa")
TIPOS_CLIENTE = ("residencia", "empresa")
STATUS_CLIENTE = ("ativo", "em_ativacao", "cancelado")
SITUACOES_ADESAO = ("rascunho", "enviada", "aprovada", "recusada")
ORIGENS_ADESAO = ("app", "site", "whatsapp")
SITUACOES_FATURA = ("paga", "em_aberto", "vencida")
CANAIS_INDICACAO = ("whatsapp", "link", "email")
SITUACOES_INDICACAO = ("pendente", "aderiu", "expirada")
TIPOS_CARTA = ("normal", "especial")
SITUACOES_CARTA = ("disponivel", "aberta", "expirada")
SITUACOES_CUPOM = ("ativo", "salvo", "usado", "expirado", "descartado")
ORIGENS_SIMULACAO = ("visitante", "cliente")
TIPOS_NOTIFICACAO = ("vencimento", "ativacao", "clube", "indicacao", "promocao")
CANAIS_NOTIFICACAO = ("app", "whatsapp", "email")
CANAIS_ATENDIMENTO = ("whatsapp", "email", "app", "ouvidoria")
STATUS_ATENDIMENTO = ("aberto", "em_andamento", "resolvido")
PAPEIS_CHAT = ("user", "assistant")
ACOES_AUDITORIA = (
    "login_ok", "login_falha", "login_bloqueado", "alerta_email", "ver_ficha", "ver_auditoria", "expurgo",
)

# Tamanhos maximos de texto usados nas tabelas novas (a camada de consultas corta antes de gravar)
TAMANHO_TITULO_CONVERSA = 120
TAMANHO_DETALHE_AUDITORIA = 500


def gerar_uuid() -> str:
    """UUID v4 em string (default das chaves UUID)."""
    return str(uuid.uuid4())


def agora_utc() -> datetime:
    """Instante atual em UTC, sem tzinfo (padrao de armazenamento do banco)."""
    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)


def _check_em(coluna: str, valores: tuple[str, ...], nome: str) -> CheckConstraint:
    """Cria uma CHECK constraint do tipo coluna IN ('a', 'b', ...)."""
    lista = ", ".join(f"'{valor}'" for valor in valores)
    return CheckConstraint(f"{coluna} IN ({lista})", name=nome)


# ---------------------------------------------------------------------------
# Painel (novo)
# ---------------------------------------------------------------------------
class Funcionario(Base):
    """Funcionario da Bulbe que acessa o painel de gestao. Origem: painel (novo)."""

    __tablename__ = "funcionarios"
    __table_args__ = (_check_em("perfil", PERFIS_FUNCIONARIO, "ck_funcionarios_perfil"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    senha_hash: Mapped[str] = mapped_column(String(255))
    perfil: Mapped[str] = mapped_column(String(20), default="atendimento")
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=agora_utc)

    chats: Mapped[list["ChatHistorico"]] = relationship(
        back_populates="funcionario", cascade="all, delete-orphan"
    )
    conversas: Mapped[list["ChatConversa"]] = relationship(
        back_populates="funcionario", cascade="all, delete-orphan"
    )


class ChatHistorico(Base):
    """
    Auditoria das perguntas feitas ao chatbot (LGPD) e base das metricas de uso/custo.
    Origem: painel (novo). As colunas de uso (modelo, tokens, custo, duracao) entraram na v2.
    """

    __tablename__ = "chat_historico"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    funcionario_id: Mapped[int] = mapped_column(ForeignKey("funcionarios.id"), index=True)
    pergunta: Mapped[str] = mapped_column(Text)
    resposta: Mapped[str] = mapped_column(Text)
    ferramentas_usadas: Mapped[str] = mapped_column(Text, default="[]")  # lista em JSON
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=agora_utc, index=True)
    # --- v2: conversa no servidor e uso/custo da API ---
    conversa_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("chat_conversas.id", ondelete="SET NULL"), index=True
    )
    modelo: Mapped[Optional[str]] = mapped_column(String(60))
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cache_read_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cache_creation_tokens: Mapped[int] = mapped_column(Integer, default=0)
    custo_estimado_usd: Mapped[float] = mapped_column(Float, default=0.0)
    duracao_ms: Mapped[Optional[int]] = mapped_column(Integer)

    funcionario: Mapped["Funcionario"] = relationship(back_populates="chats")


class ChatConversa(Base):
    """Conversa do chatbot guardada no servidor (v2). Origem: painel (novo)."""

    __tablename__ = "chat_conversas"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gerar_uuid)
    funcionario_id: Mapped[int] = mapped_column(ForeignKey("funcionarios.id"), index=True)
    titulo: Mapped[str] = mapped_column(String(TAMANHO_TITULO_CONVERSA))
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=agora_utc)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime, default=agora_utc, index=True)

    funcionario: Mapped["Funcionario"] = relationship(back_populates="conversas")
    mensagens: Mapped[list["ChatMensagem"]] = relationship(
        back_populates="conversa", cascade="all, delete-orphan", order_by="ChatMensagem.ordem"
    )


class ChatMensagem(Base):
    """
    Mensagem de uma conversa do chatbot (v2). conteudo_json guarda o conteudo EXATO enviado/recebido
    da API (lista de blocos ou string, em JSON); texto e o que a interface mostra (pode ser vazio).
    O historico e so de acrescimo: as mensagens nunca sao alteradas depois de gravadas.
    """

    __tablename__ = "chat_mensagens"
    __table_args__ = (
        UniqueConstraint("conversa_id", "ordem", name="uq_chat_mensagens_conversa_ordem"),
        _check_em("papel", PAPEIS_CHAT, "ck_chat_mensagens_papel"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversa_id: Mapped[str] = mapped_column(ForeignKey("chat_conversas.id", ondelete="CASCADE"), index=True)
    ordem: Mapped[int] = mapped_column(Integer)
    papel: Mapped[str] = mapped_column(String(20))
    conteudo_json: Mapped[str] = mapped_column(Text)
    texto: Mapped[str] = mapped_column(Text, default="")
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=agora_utc)

    conversa: Mapped["ChatConversa"] = relationship(back_populates="mensagens")


class AuditoriaAcesso(Base):
    """
    Trilha de auditoria do painel (v2): logins, bloqueios, alertas, fichas vistas e expurgos.
    funcionario_id e nulo em login falho de e-mail inexistente. Origem: painel (novo).
    """

    __tablename__ = "auditoria_acessos"
    __table_args__ = (_check_em("acao", ACOES_AUDITORIA, "ck_auditoria_acessos_acao"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    funcionario_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("funcionarios.id", ondelete="SET NULL"), index=True
    )
    email_informado: Mapped[Optional[str]] = mapped_column(String(160), index=True)
    acao: Mapped[str] = mapped_column(String(30), index=True)
    recurso_tipo: Mapped[Optional[str]] = mapped_column(String(40))
    recurso_id: Mapped[Optional[str]] = mapped_column(String(64))
    ip: Mapped[Optional[str]] = mapped_column(String(45))
    detalhe: Mapped[Optional[str]] = mapped_column(String(TAMANHO_DETALHE_AUDITORIA))
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=agora_utc, index=True)

    funcionario: Mapped[Optional["Funcionario"]] = relationship()


# ---------------------------------------------------------------------------
# Bulbe (ja existe no app/site)
# ---------------------------------------------------------------------------
class Usina(Base):
    """Usina solar que gera os creditos de energia. Origem: Bulbe."""

    __tablename__ = "usinas"
    __table_args__ = (
        _check_em("status", STATUS_USINA, "ck_usinas_status"),
        CheckConstraint("capacidade_geracao_kwh > 0", name="ck_usinas_capacidade"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(100))
    localizacao: Mapped[str] = mapped_column(String(100))
    capacidade_geracao_kwh: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(20), default="ativa")
    data_ativacao: Mapped[date] = mapped_column(Date)

    clientes: Mapped[list["Cliente"]] = relationship(back_populates="usina")


class Cliente(Base):
    """Cliente da Bulbe (assinante de energia solar). Origem: Bulbe."""

    __tablename__ = "clientes"
    __table_args__ = (
        _check_em("tipo", TIPOS_CLIENTE, "ck_clientes_tipo"),
        _check_em("status", STATUS_CLIENTE, "ck_clientes_status"),
        CheckConstraint("length(cpf) = 11", name="ck_clientes_cpf_11_digitos"),
        CheckConstraint("length(uf) = 2", name="ck_clientes_uf"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gerar_uuid)
    nome: Mapped[str] = mapped_column(String(120), index=True)
    email: Mapped[str] = mapped_column(String(160), index=True)
    cpf: Mapped[str] = mapped_column(String(11), unique=True)  # so digitos
    telefone: Mapped[str] = mapped_column(String(11))  # so digitos, com DDD
    tipo: Mapped[str] = mapped_column(String(20), default="residencia")
    cep: Mapped[str] = mapped_column(String(8))
    logradouro: Mapped[str] = mapped_column(String(120))
    numero: Mapped[str] = mapped_column(String(10))
    complemento: Mapped[Optional[str]] = mapped_column(String(60))
    bairro: Mapped[str] = mapped_column(String(80))
    cidade: Mapped[str] = mapped_column(String(80), index=True)
    uf: Mapped[str] = mapped_column(String(2), default="MG")
    distribuidora: Mapped[str] = mapped_column(String(40), default="CEMIG")
    numero_instalacao: Mapped[str] = mapped_column(String(20), unique=True)
    usina_id: Mapped[Optional[int]] = mapped_column(ForeignKey("usinas.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="em_ativacao", index=True)
    codigo_indicacao: Mapped[str] = mapped_column(String(30), unique=True)
    app_acesso_habilitado: Mapped[bool] = mapped_column(Boolean, default=False)
    ultimo_login_app: Mapped[Optional[datetime]] = mapped_column(DateTime)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=agora_utc)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime, default=agora_utc, onupdate=agora_utc)

    usina: Mapped[Optional["Usina"]] = relationship(back_populates="clientes")
    adesoes: Mapped[list["Adesao"]] = relationship(back_populates="cliente")
    ativacao: Mapped[Optional["Ativacao"]] = relationship(
        back_populates="cliente", cascade="all, delete-orphan", uselist=False
    )
    eventos_ativacao: Mapped[list["AtivacaoEvento"]] = relationship(
        back_populates="cliente", cascade="all, delete-orphan", order_by="AtivacaoEvento.ocorrido_em"
    )
    faturas: Mapped[list["Fatura"]] = relationship(
        back_populates="cliente", cascade="all, delete-orphan", order_by="Fatura.mes_referencia"
    )
    indicacoes: Mapped[list["Indicacao"]] = relationship(
        back_populates="cliente", cascade="all, delete-orphan"
    )
    clube: Mapped[Optional["ClubeStatus"]] = relationship(
        back_populates="cliente", cascade="all, delete-orphan", uselist=False
    )
    cartas: Mapped[list["Carta"]] = relationship(
        back_populates="cliente", cascade="all, delete-orphan", foreign_keys="Carta.cliente_id"
    )
    cupons: Mapped[list["Cupom"]] = relationship(
        back_populates="cliente", cascade="all, delete-orphan", foreign_keys="Cupom.cliente_id"
    )
    simulacoes: Mapped[list["Simulacao"]] = relationship(back_populates="cliente")
    notificacoes: Mapped[list["Notificacao"]] = relationship(
        back_populates="cliente", cascade="all, delete-orphan"
    )
    atendimentos: Mapped[list["Atendimento"]] = relationship(
        back_populates="cliente", cascade="all, delete-orphan"
    )


class Fatura(Base):
    """Fatura mensal do cliente (2a via / historico). Origem: Bulbe."""

    __tablename__ = "faturas"
    __table_args__ = (
        UniqueConstraint("cliente_id", "mes_referencia", name="uq_faturas_cliente_mes"),
        _check_em("situacao", SITUACOES_FATURA, "ck_faturas_situacao"),
        CheckConstraint("length(mes_referencia) = 7", name="ck_faturas_mes_referencia"),
        CheckConstraint("consumo_kwh >= 0", name="ck_faturas_consumo"),
        CheckConstraint(
            "desconto >= 0 AND bonus_indicacao >= 0 AND bonus_clube >= 0", name="ck_faturas_descontos"
        ),
        CheckConstraint("valor_total >= 0", name="ck_faturas_valor_total"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cliente_id: Mapped[str] = mapped_column(ForeignKey("clientes.id"), index=True)
    mes_referencia: Mapped[str] = mapped_column(String(7))  # AAAA-MM
    consumo_kwh: Mapped[float] = mapped_column(Float)
    valor_sem_bulbe: Mapped[float] = mapped_column(Float)
    desconto: Mapped[float] = mapped_column(Float, default=0.0)
    bonus_indicacao: Mapped[float] = mapped_column(Float, default=0.0)
    # v2: bonus especial de R$ 50 do Clube Bulbe (5 semanas seguidas), aplicado na fatura seguinte
    bonus_clube: Mapped[float] = mapped_column(Float, default=0.0)
    valor_total: Mapped[float] = mapped_column(Float)
    vencimento: Mapped[date] = mapped_column(Date, index=True)
    situacao: Mapped[str] = mapped_column(String(20), default="em_aberto", index=True)
    pago_em: Mapped[Optional[date]] = mapped_column(Date)

    cliente: Mapped["Cliente"] = relationship(back_populates="faturas")


class Indicacao(Base):
    """Indicacao feita por um cliente (Indique e Ganhe, R$ 50). Origem: Bulbe."""

    __tablename__ = "indicacoes"
    __table_args__ = (
        _check_em("canal", CANAIS_INDICACAO, "ck_indicacoes_canal"),
        _check_em("situacao", SITUACOES_INDICACAO, "ck_indicacoes_situacao"),
        CheckConstraint("bonus >= 0", name="ck_indicacoes_bonus"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gerar_uuid)
    cliente_id: Mapped[str] = mapped_column(ForeignKey("clientes.id"), index=True)
    nome_indicado: Mapped[str] = mapped_column(String(120))
    contato_indicado: Mapped[str] = mapped_column(String(160))
    canal: Mapped[str] = mapped_column(String(20), default="whatsapp")
    situacao: Mapped[str] = mapped_column(String(20), default="pendente", index=True)
    bonus: Mapped[float] = mapped_column(Float, default=50.0)
    creditado_em: Mapped[Optional[date]] = mapped_column(Date)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=agora_utc)

    cliente: Mapped["Cliente"] = relationship(back_populates="indicacoes")


class Notificacao(Base):
    """Notificacao enviada ao cliente (app, WhatsApp ou e-mail). Origem: Bulbe."""

    __tablename__ = "notificacoes"
    __table_args__ = (
        _check_em("tipo", TIPOS_NOTIFICACAO, "ck_notificacoes_tipo"),
        _check_em("canal", CANAIS_NOTIFICACAO, "ck_notificacoes_canal"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cliente_id: Mapped[str] = mapped_column(ForeignKey("clientes.id"), index=True)
    tipo: Mapped[str] = mapped_column(String(20))
    titulo: Mapped[str] = mapped_column(String(120))
    mensagem: Mapped[str] = mapped_column(String(500))
    canal: Mapped[str] = mapped_column(String(20), default="app")
    enviada_em: Mapped[datetime] = mapped_column(DateTime, default=agora_utc)
    lida: Mapped[bool] = mapped_column(Boolean, default=False)

    cliente: Mapped["Cliente"] = relationship(back_populates="notificacoes")


class Atendimento(Base):
    """Atendimento/chamado aberto pelo cliente. Origem: Bulbe."""

    __tablename__ = "atendimentos"
    __table_args__ = (
        _check_em("canal", CANAIS_ATENDIMENTO, "ck_atendimentos_canal"),
        _check_em("status", STATUS_ATENDIMENTO, "ck_atendimentos_status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cliente_id: Mapped[str] = mapped_column(ForeignKey("clientes.id"), index=True)
    canal: Mapped[str] = mapped_column(String(20))
    assunto: Mapped[str] = mapped_column(String(120))
    descricao: Mapped[str] = mapped_column(String(1000))
    status: Mapped[str] = mapped_column(String(20), default="aberto", index=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=agora_utc)
    resolvido_em: Mapped[Optional[datetime]] = mapped_column(DateTime)

    cliente: Mapped["Cliente"] = relationship(back_populates="atendimentos")


# ---------------------------------------------------------------------------
# Squad Cleanergy (funcionalidades novas) + adesao (squad pelo app, Bulbe pelo site)
# ---------------------------------------------------------------------------
class Adesao(Base):
    """Solicitacao de adesao (app da squad ou site da Bulbe)."""

    __tablename__ = "adesoes"
    __table_args__ = (
        _check_em("situacao", SITUACOES_ADESAO, "ck_adesoes_situacao"),
        _check_em("origem", ORIGENS_ADESAO, "ck_adesoes_origem"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gerar_uuid)
    nome: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(160))
    cpf: Mapped[Optional[str]] = mapped_column(String(11))
    telefone: Mapped[Optional[str]] = mapped_column(String(11))
    cidade: Mapped[Optional[str]] = mapped_column(String(80))
    uf: Mapped[Optional[str]] = mapped_column(String(2))
    distribuidora: Mapped[Optional[str]] = mapped_column(String(40))
    numero_instalacao: Mapped[Optional[str]] = mapped_column(String(20))
    valor_conta_atual: Mapped[Optional[float]] = mapped_column(Float)
    economia_mensal_estimada: Mapped[Optional[float]] = mapped_column(Float)
    situacao: Mapped[str] = mapped_column(String(20), default="rascunho", index=True)
    origem: Mapped[str] = mapped_column(String(20), default="app")
    cliente_id: Mapped[Optional[str]] = mapped_column(ForeignKey("clientes.id"), index=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=agora_utc)

    cliente: Mapped[Optional["Cliente"]] = relationship(back_populates="adesoes")


class Ativacao(Base):
    """Situacao atual da jornada de ativacao em 5 etapas. Origem: squad."""

    __tablename__ = "ativacoes"
    __table_args__ = (
        CheckConstraint("etapa_atual BETWEEN 1 AND 5", name="ck_ativacoes_etapa"),
    )

    cliente_id: Mapped[str] = mapped_column(ForeignKey("clientes.id"), primary_key=True)
    etapa_atual: Mapped[int] = mapped_column(Integer, default=1)
    previsao_conclusao: Mapped[date] = mapped_column(Date)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime, default=agora_utc)

    cliente: Mapped["Cliente"] = relationship(back_populates="ativacao")


class AtivacaoEvento(Base):
    """Historico de eventos da ativacao (ex.: protocolo aberto na CEMIG). Origem: squad."""

    __tablename__ = "ativacao_eventos"
    __table_args__ = (
        CheckConstraint("etapa BETWEEN 1 AND 5", name="ck_ativacao_eventos_etapa"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cliente_id: Mapped[str] = mapped_column(ForeignKey("clientes.id"), index=True)
    etapa: Mapped[int] = mapped_column(Integer)
    observacao: Mapped[str] = mapped_column(String(500))
    ocorrido_em: Mapped[datetime] = mapped_column(DateTime, default=agora_utc)

    cliente: Mapped["Cliente"] = relationship(back_populates="eventos_ativacao")


class Parceiro(Base):
    """Parceiro do Clube Bulbe (ex.: Araujo, Inter, Livelo). Origem: squad."""

    __tablename__ = "parceiros"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gerar_uuid)
    nome: Mapped[str] = mapped_column(String(100), unique=True)
    categoria: Mapped[str] = mapped_column(String(60))
    logo_url: Mapped[Optional[str]] = mapped_column(String(255))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=agora_utc)

    cupons: Mapped[list["Cupom"]] = relationship(back_populates="parceiro")


class ClubeStatus(Base):
    """Sequencia semanal do cliente no Clube Bulbe (meta de 5 semanas). Origem: squad."""

    __tablename__ = "clube_status"
    __table_args__ = (
        CheckConstraint("semanas_sequencia BETWEEN 0 AND 5", name="ck_clube_status_sequencia"),
        CheckConstraint("meta_sequencia > 0", name="ck_clube_status_meta"),
    )

    cliente_id: Mapped[str] = mapped_column(ForeignKey("clientes.id"), primary_key=True)
    semanas_sequencia: Mapped[int] = mapped_column(Integer, default=0)
    meta_sequencia: Mapped[int] = mapped_column(Integer, default=5)
    proxima_carta_em: Mapped[Optional[datetime]] = mapped_column(DateTime)
    bonus_especial_pendente: Mapped[bool] = mapped_column(Boolean, default=False)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime, default=agora_utc)

    cliente: Mapped["Cliente"] = relationship(back_populates="clube")


class Carta(Base):
    """Carta semanal do Clube Bulbe. Ao ser aberta gera um cupom. Origem: squad."""

    __tablename__ = "cartas"
    __table_args__ = (
        _check_em("tipo", TIPOS_CARTA, "ck_cartas_tipo"),
        _check_em("situacao", SITUACOES_CARTA, "ck_cartas_situacao"),
        UniqueConstraint("cliente_id", "semana", name="uq_cartas_cliente_semana"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gerar_uuid)
    cliente_id: Mapped[str] = mapped_column(ForeignKey("clientes.id"), index=True)
    semana: Mapped[int] = mapped_column(Integer)
    tipo: Mapped[str] = mapped_column(String(20), default="normal")
    situacao: Mapped[str] = mapped_column(String(20), default="disponivel")
    disponivel_em: Mapped[datetime] = mapped_column(DateTime)
    aberta_em: Mapped[Optional[datetime]] = mapped_column(DateTime)
    # FK circular com cupons.carta_id: use_alter + post_update evitam problema de ordem no INSERT/DROP.
    cupom_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("cupons.id", use_alter=True, name="fk_cartas_cupom_id")
    )

    cliente: Mapped["Cliente"] = relationship(back_populates="cartas", foreign_keys=[cliente_id])
    cupom: Mapped[Optional["Cupom"]] = relationship(foreign_keys=[cupom_id], post_update=True)


class Cupom(Base):
    """Cupom gerado pela abertura de uma carta (valido por 14 dias). Origem: squad."""

    __tablename__ = "cupons"
    __table_args__ = (_check_em("situacao", SITUACOES_CUPOM, "ck_cupons_situacao"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gerar_uuid)
    cliente_id: Mapped[str] = mapped_column(ForeignKey("clientes.id"), index=True)
    carta_id: Mapped[Optional[str]] = mapped_column(ForeignKey("cartas.id"), index=True)
    parceiro_id: Mapped[Optional[str]] = mapped_column(ForeignKey("parceiros.id"), index=True)
    titulo: Mapped[str] = mapped_column(String(120))
    descricao: Mapped[str] = mapped_column(String(300))
    codigo: Mapped[Optional[str]] = mapped_column(String(30))
    situacao: Mapped[str] = mapped_column(String(20), default="ativo", index=True)
    aberto_em: Mapped[datetime] = mapped_column(DateTime, default=agora_utc)
    valido_ate: Mapped[date] = mapped_column(Date)
    usado_em: Mapped[Optional[datetime]] = mapped_column(DateTime)

    cliente: Mapped["Cliente"] = relationship(back_populates="cupons", foreign_keys=[cliente_id])
    carta: Mapped[Optional["Carta"]] = relationship(foreign_keys=[carta_id])
    parceiro: Mapped[Optional["Parceiro"]] = relationship(back_populates="cupons")


class Dica(Base):
    """Dica de economia de energia exibida no carrossel do app. Origem: squad."""

    __tablename__ = "dicas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    titulo: Mapped[str] = mapped_column(String(100))
    descricao: Mapped[str] = mapped_column(String(250))
    economia_mensal: Mapped[float] = mapped_column(Float)
    economia_anual: Mapped[float] = mapped_column(Float)
    ordem: Mapped[int] = mapped_column(Integer, default=1)


class Simulacao(Base):
    """Registro de uso do simulador de economia (visitante sem login ou cliente). Origem: squad."""

    __tablename__ = "simulacoes"
    __table_args__ = (
        _check_em("origem", ORIGENS_SIMULACAO, "ck_simulacoes_origem"),
        CheckConstraint("valor_conta > 0", name="ck_simulacoes_valor_conta"),
        CheckConstraint("meses BETWEEN 1 AND 60", name="ck_simulacoes_meses"),
        CheckConstraint("amigos_indicados >= 0", name="ck_simulacoes_amigos"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    origem: Mapped[str] = mapped_column(String(20), default="visitante")
    cliente_id: Mapped[Optional[str]] = mapped_column(ForeignKey("clientes.id"), index=True)
    valor_conta: Mapped[float] = mapped_column(Float)
    meses: Mapped[int] = mapped_column(Integer, default=12)
    amigos_indicados: Mapped[int] = mapped_column(Integer, default=0)
    economia_total: Mapped[float] = mapped_column(Float)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=agora_utc, index=True)

    cliente: Mapped[Optional["Cliente"]] = relationship(back_populates="simulacoes")
