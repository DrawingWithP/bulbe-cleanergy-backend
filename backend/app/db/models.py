"""
Modelos ORM (SQLAlchemy 2): como os dados ficam guardados no banco.

O Dominio (app/domain) continua em Pydantic e define o que a API recebe,
valida e devolve. Estes modelos sao conhecidos apenas pelos repositorios,
que convertem os modelos ORM em objetos do Dominio antes de devolve-los.

Chaves estrangeiras (FK):
- ativacoes, cartas, cupons, ofensivas_clube e verificacoes_primeiro_acesso
  apontam para clientes.id. Ao remover um cliente, o banco remove os filhos
  por meio de ON DELETE CASCADE.
- cupons.carta_id aponta para cartas.id e utiliza ON DELETE SET NULL.
- cartas.cupom_id nao e uma FK, evitando um ciclo entre cartas e cupons.
- cupons guarda um retrato do parceiro, sem FK. Assim, o cupom continua
  valido mesmo que o parceiro seja removido do Clube.
- indicacoes.cliente_id aponta para clientes.id (UUID em texto) com
  ON DELETE CASCADE.
- simulacoes.cliente_id e opcional (simulador aberto, sem login) e utiliza
  ON DELETE SET NULL.
- bandeiras_tarifarias guarda a bandeira vigente de cada mes, usada no
  calculo de economia do simulador.
"""

from datetime import date, datetime

from sqlalchemy import (
    JSON,
    false as sa_false,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from app.db.database import Base


# --------------------------------------------------------------------------
# Painel administrativo
# --------------------------------------------------------------------------


class UsuarioModel(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    nome: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )

    senha_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )


class UsinaModel(Base):
    __tablename__ = "usinas"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    nome: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    localizacao: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    capacidade_geracao_kwh: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    data_ativacao: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )


class DicaModel(Base):
    __tablename__ = "dicas"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    titulo: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    descricao: Mapped[str] = mapped_column(
        String(250),
        nullable=False,
    )

    economia: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    imagem_svg: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    icone: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="lampada_led",
        server_default="lampada_led",
    )

    # Vitrine do app: exatamente 5 dicas em exibicao, com ordem 1..5.
    em_exibicao: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=sa_false(),
    )

    ordem: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    data_ativacao: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )


# --------------------------------------------------------------------------
# Captacao: adesoes, simulacoes e indicacoes
# --------------------------------------------------------------------------


class AdesaoModel(Base):
    __tablename__ = "adesoes"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    nome: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    email: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    cpf: Mapped[str] = mapped_column(
        String(11),
        index=True,
        nullable=False,
    )

    telefone: Mapped[str] = mapped_column(
        String(12),
        nullable=False,
    )

    cep: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
    )

    logradouro: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    numero: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    bairro: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
    )

    cidade: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
    )

    uf: Mapped[str] = mapped_column(
        String(2),
        nullable=False,
    )

    distribuidora: Mapped[str] = mapped_column(
        String(15),
        nullable=False,
    )

    numero_instalacao: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    valor_conta_atual: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    data_ativacao: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )


class SimulacaoModel(Base):
    __tablename__ = "simulacoes"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    valor_atual: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    valor_proposto: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    periodo_meses: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    indicacoes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    data_ativacao: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    # Simulador logado: cliente que simulou. Vazio no simulador aberto.
    cliente_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey(
            "clientes.id",
            ondelete="SET NULL",
        ),
        index=True,
        nullable=True,
    )

    # Bandeira tarifaria usada no calculo (RF-03).
    bandeira: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="verde",
        server_default="verde",
    )

    economia_mensal: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    economia_total: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )


class BandeiraTarifariaModel(Base):
    """
    Bandeira tarifaria vigente em cada mes (AAAA-MM).
    """

    __tablename__ = "bandeiras_tarifarias"

    mes_referencia: Mapped[str] = mapped_column(
        String(7),
        primary_key=True,
    )

    bandeira: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )


class IndicacaoModel(Base):
    __tablename__ = "indicacoes"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    cliente_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey(
            "clientes.id",
            ondelete="CASCADE",
        ),
        index=True,
        nullable=False,
    )

    nome: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    contato: Mapped[str] = mapped_column(
        String(100),
        index=True,
        nullable=False,
    )

    situacao: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    bonus: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )


# --------------------------------------------------------------------------
# Clientes e jornada no app
# --------------------------------------------------------------------------


class ClienteModel(Base):
    __tablename__ = "clientes"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
    )

    nome: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )

    cpf: Mapped[str] = mapped_column(
        String(11),
        unique=True,
        index=True,
        nullable=False,
    )

    telefone: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    # Endereco: objeto aninhado no Dominio e colunas na tabela.
    cep: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    logradouro: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    numero: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    complemento: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    bairro: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    cidade: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    uf: Mapped[str] = mapped_column(
        String(2),
        nullable=False,
    )

    distribuidora: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    numero_instalacao: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    acesso_habilitado: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    criado_em: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )


class AtivacaoModel(Base):
    """
    Jornada de ativacao CEMIG.

    Existe uma linha por cliente, sendo cliente_id
    simultaneamente chave primaria e chave estrangeira.
    """

    __tablename__ = "ativacoes"

    cliente_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey(
            "clientes.id",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )

    etapa_atual: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    distribuidora: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    prazo_ativacao_dias: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    previsao_conclusao: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    atualizado_em: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    observacoes: Mapped[list[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )


class VerificacaoModel(Base):
    """
    Codigo de confirmacao do primeiro acesso
    (US-09 e US-10).
    """

    __tablename__ = "verificacoes_primeiro_acesso"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
    )

    cliente_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey(
            "clientes.id",
            ondelete="CASCADE",
        ),
        index=True,
        nullable=False,
    )

    cpf: Mapped[str] = mapped_column(
        String(11),
        nullable=False,
    )

    canal: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    codigo: Mapped[str] = mapped_column(
        String(6),
        nullable=False,
    )

    destino_mascarado: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    expira_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    tentativas: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    situacao: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )


# --------------------------------------------------------------------------
# Clube Bulbe: parceiros, cartas, cupons e ofensiva
# --------------------------------------------------------------------------


class ParceiroModel(Base):
    __tablename__ = "parceiros"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
    )

    nome: Mapped[str] = mapped_column(
        String(100),
        index=True,
        nullable=False,
    )

    categoria: Mapped[str] = mapped_column(
        String(60),
        nullable=False,
    )

    logo_url: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    ativo: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    criado_em: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    atualizado_em: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )


class CartaModel(Base):
    __tablename__ = "cartas"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
    )

    cliente_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey(
            "clientes.id",
            ondelete="CASCADE",
        ),
        index=True,
        nullable=False,
    )

    semana: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    tipo: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    situacao: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    disponivel_em: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    aberta_em: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    # Nao utiliza FK para evitar ciclo entre cartas e cupons.
    cupom_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
    )


class CupomModel(Base):
    __tablename__ = "cupons"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
    )

    cliente_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey(
            "clientes.id",
            ondelete="CASCADE",
        ),
        index=True,
        nullable=False,
    )

    carta_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey(
            "cartas.id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    tag: Mapped[str] = mapped_column(
        String(60),
        nullable=False,
    )

    titulo: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )

    descricao: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
    )

    codigo: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    # Retrato do parceiro no momento da emissao do cupom.
    parceiro_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
    )

    parceiro_nome: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    parceiro_categoria: Mapped[str] = mapped_column(
        String(60),
        nullable=False,
    )

    situacao: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    valido_ate: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    dias_restantes: Mapped[int] = mapped_column(
        Integer,
        default=14,
        nullable=False,
    )

    criado_em: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    usado_em: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    # Modelo do catalogo que gerou o cupom (copia, sem FK: o cupom continua
    # valido mesmo se o modelo for removido do catalogo).
    modelo_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
    )


class OfensivaClubeModel(Base):
    """
    Semanas seguidas em que o cliente abriu
    uma carta do Clube Bulbe.
    """

    __tablename__ = "ofensivas_clube"

    cliente_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey(
            "clientes.id",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )

    semanas_sequencia: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )


# --------------------------------------------------------------------------
# Demonstracao
# --------------------------------------------------------------------------


class RelogioDemonstracaoModel(Base):
    """
    Deslocamento do relogio usado na demonstracao (pular dias).
    Uma unica linha (id = 1). Ignorado em producao.
    """

    __tablename__ = "relogio_demonstracao"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    deslocamento_segundos: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )


class CupomCatalogoModel(Base):
    """
    Modelo de cupom do Clube Bulbe (catalogo). A cada carta normal aberta,
    um modelo ativo e sorteado e vira um cupom do cliente com codigo unico.
    """

    __tablename__ = "cupons_catalogo"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
    )

    parceiro_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey(
            "parceiros.id",
            ondelete="CASCADE",
        ),
        index=True,
        nullable=False,
    )

    titulo: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )

    descricao: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
    )

    tag: Mapped[str] = mapped_column(
        String(60),
        nullable=False,
    )

    prefixo_codigo: Mapped[str] = mapped_column(
        String(12),
        nullable=False,
    )

    validade_dias: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    peso: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )

    ativo: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    criado_em: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    atualizado_em: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )


# --------------------------------------------------------------------------
# Atendimento (chat do app com robo e atendente)
# --------------------------------------------------------------------------


class AtendimentoModel(Base):
    """Conversa do cliente com o atendimento (robo e, se pedir, atendente)."""

    __tablename__ = "atendimentos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    cliente_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("clientes.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    assunto: Mapped[str] = mapped_column(String(120), nullable=False)

    # bot | aguardando_atendente | em_atendimento | resolvido
    status: Mapped[str] = mapped_column(String(30), index=True, nullable=False)

    atendente_nome: Mapped[str | None] = mapped_column(String(100), nullable=True)

    avaliacao: Mapped[int | None] = mapped_column(Integer, nullable=True)

    criado_em: Mapped[str] = mapped_column(String(30), nullable=False)

    atualizado_em: Mapped[str] = mapped_column(String(30), nullable=False)

    encerrado_em: Mapped[str | None] = mapped_column(String(30), nullable=True)


class AtendimentoMensagemModel(Base):
    """Mensagem de uma conversa de atendimento."""

    __tablename__ = "atendimento_mensagens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    atendimento_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("atendimentos.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    # cliente | bot | atendente | sistema
    autor: Mapped[str] = mapped_column(String(20), nullable=False)

    texto: Mapped[str] = mapped_column(Text, nullable=False)

    # Botoes de resposta rapida (so nas mensagens do robo)
    opcoes: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    criado_em: Mapped[str] = mapped_column(String(30), nullable=False)
