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
- indicacoes.cliente_id ainda e inteiro no Dominio, enquanto clientes.id
  utiliza UUID em texto. Por isso, ainda nao existe FK entre essas tabelas.
"""

from datetime import date, datetime

from sqlalchemy import (
    JSON,
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

    imagem_svg: Mapped[str] = mapped_column(
        Text,
        nullable=False,
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


class IndicacaoModel(Base):
    __tablename__ = "indicacoes"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    cliente_id: Mapped[int] = mapped_column(
        Integer,
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
