"""
Modelos ORM (SQLAlchemy 2): como os dados ficam guardados no banco.

O Dominio (app/domain) continua em Pydantic e define o que a API recebe,
valida e devolve. Estes modelos so sao conhecidos pelos repositorios,
que convertem UsinaModel -> Usina (e assim por diante) antes de devolver.

Chaves estrangeiras (FK):
- ativacoes, cartas, cupons, ofensivas_clube e verificacoes_primeiro_acesso
  apontam para clientes.id. Ao remover um cliente, o banco remove os filhos
  (ON DELETE CASCADE).
- cupons.carta_id aponta para cartas.id (SET NULL se a carta sumir).
- cartas.cupom_id NAO e FK: cupom ja aponta para a carta, e uma FK nos dois
  sentidos criaria um ciclo entre as tabelas.
- cupons guarda um "retrato" do parceiro (id, nome, categoria) sem FK:
  o cupom emitido continua valido mesmo que o parceiro saia do Clube (US-26).
- indicacoes.cliente_id e inteiro no Dominio, enquanto clientes.id e UUID
  (texto). Por isso ainda nao ha FK ali; fica como pendencia de modelagem.
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
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base

# --------------------------------------------------------------------------
# Painel administrativo
# --------------------------------------------------------------------------


class UsuarioModel(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    senha_hash: Mapped[str] = mapped_column(String(255))


class UsinaModel(Base):
    __tablename__ = "usinas"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(100))
    localizacao: Mapped[str] = mapped_column(String(100))
    capacidade_geracao_kwh: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(20))
    data_ativacao: Mapped[date] = mapped_column(Date)


class DicaModel(Base):
    __tablename__ = "dicas"

    id: Mapped[int] = mapped_column(primary_key=True)
    titulo: Mapped[str] = mapped_column(String(100))
    descricao: Mapped[str] = mapped_column(String(250))
    economia: Mapped[float] = mapped_column(Float)
    imagem_svg: Mapped[str] = mapped_column(Text)
    data_ativacao: Mapped[date] = mapped_column(Date)


# --------------------------------------------------------------------------
# Captacao: adesoes, simulacoes e indicacoes
# --------------------------------------------------------------------------


class AdesaoModel(Base):
    __tablename__ = "adesoes"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(100))
    cpf: Mapped[str] = mapped_column(String(11), index=True)
    telefone: Mapped[str] = mapped_column(String(12))
    cep: Mapped[str] = mapped_column(String(8))
    logradouro: Mapped[str] = mapped_column(String(100))
    numero: Mapped[int] = mapped_column(Integer)
    bairro: Mapped[str] = mapped_column(String(40))
    cidade: Mapped[str] = mapped_column(String(40))
    uf: Mapped[str] = mapped_column(String(2))
    distribuidora: Mapped[str] = mapped_column(String(15))
    numero_instalacao: Mapped[str] = mapped_column(String(30))
    valor_conta_atual: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(20))
    data_ativacao: Mapped[date] = mapped_column(Date)


class SimulacaoModel(Base):
    __tablename__ = "simulacoes"

    id: Mapped[int] = mapped_column(primary_key=True)
    valor_atual: Mapped[float] = mapped_column(Float)
    valor_proposto: Mapped[float] = mapped_column(Float)
    periodo_meses: Mapped[int] = mapped_column(Integer)
    indicacoes: Mapped[int] = mapped_column(Integer)
    data_ativacao: Mapped[date] = mapped_column(Date)


class IndicacaoModel(Base):
    __tablename__ = "indicacoes"

    id: Mapped[int] = mapped_column(primary_key=True)
    cliente_id: Mapped[int] = mapped_column(Integer, index=True)
    nome: Mapped[str] = mapped_column(String(100))
    contato: Mapped[str] = mapped_column(String(100), index=True)
    situacao: Mapped[str] = mapped_column(String(20))
    bonus: Mapped[float] = mapped_column(Float)


# --------------------------------------------------------------------------
# Clientes e jornada no app
# --------------------------------------------------------------------------


class ClienteModel(Base):
    __tablename__ = "clientes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    nome: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    cpf: Mapped[str] = mapped_column(String(11), unique=True, index=True)
    telefone: Mapped[str] = mapped_column(String(20))
    # Endereco (objeto aninhado no Dominio, colunas na tabela)
    cep: Mapped[str] = mapped_column(String(10))
    logradouro: Mapped[str] = mapped_column(String(150))
    numero: Mapped[str] = mapped_column(String(20))
    complemento: Mapped[str | None] = mapped_column(String(100))
    bairro: Mapped[str] = mapped_column(String(100))
    cidade: Mapped[str] = mapped_column(String(100))
    uf: Mapped[str] = mapped_column(String(2))
    distribuidora: Mapped[str] = mapped_column(String(50))
    numero_instalacao: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(20))
    acesso_habilitado: Mapped[bool] = mapped_column(Boolean, default=False)
    criado_em: Mapped[str] = mapped_column(String(30))


class AtivacaoModel(Base):
    """Jornada de ativacao CEMIG: uma linha por cliente (PK = FK)."""

    __tablename__ = "ativacoes"

    cliente_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("clientes.id", ondelete="CASCADE"), primary_key=True
    )
    etapa_atual: Mapped[int] = mapped_column(Integer)
    distribuidora: Mapped[str] = mapped_column(String(50))
    prazo_ativacao_dias: Mapped[int] = mapped_column(Integer)
    previsao_conclusao: Mapped[str] = mapped_column(String(10))
    atualizado_em: Mapped[str] = mapped_column(String(30))
    observacoes: Mapped[list[str]] = mapped_column(JSON, default=list)


class VerificacaoModel(Base):
    """Codigo de confirmacao do primeiro acesso (US-09 e US-10)."""

    __tablename__ = "verificacoes_primeiro_acesso"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    cliente_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("clientes.id", ondelete="CASCADE"), index=True
    )
    cpf: Mapped[str] = mapped_column(String(11))
    canal: Mapped[str] = mapped_column(String(20))
    codigo: Mapped[str] = mapped_column(String(10))
    destino_mascarado: Mapped[str] = mapped_column(String(50))
    expira_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    tentativas: Mapped[int] = mapped_column(Integer, default=0)
    situacao: Mapped[str] = mapped_column(String(20))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))


# --------------------------------------------------------------------------
# Clube Bulbe: parceiros, cartas, cupons e ofensiva
# --------------------------------------------------------------------------


class ParceiroModel(Base):
    __tablename__ = "parceiros"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    nome: Mapped[str] = mapped_column(String(100), index=True)
    categoria: Mapped[str] = mapped_column(String(60))
    logo_url: Mapped[str | None] = mapped_column(String(255))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    criado_em: Mapped[str] = mapped_column(String(30))
    atualizado_em: Mapped[str | None] = mapped_column(String(30))


class CartaModel(Base):
    __tablename__ = "cartas"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    cliente_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("clientes.id", ondelete="CASCADE"), index=True
    )
    semana: Mapped[int] = mapped_column(Integer)
    tipo: Mapped[str] = mapped_column(String(20))
    situacao: Mapped[str] = mapped_column(String(20))
    disponivel_em: Mapped[str] = mapped_column(String(30))
    aberta_em: Mapped[str | None] = mapped_column(String(30))
    cupom_id: Mapped[str | None] = mapped_column(String(36))


class CupomModel(Base):
    __tablename__ = "cupons"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    cliente_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("clientes.id", ondelete="CASCADE"), index=True
    )
    carta_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("cartas.id", ondelete="SET NULL")
    )
    tag: Mapped[str] = mapped_column(String(60))
    titulo: Mapped[str] = mapped_column(String(120))
    descricao: Mapped[str] = mapped_column(String(300))
    codigo: Mapped[str] = mapped_column(String(30))
    parceiro_id: Mapped[str] = mapped_column(String(36))
    parceiro_nome: Mapped[str] = mapped_column(String(100))
    parceiro_categoria: Mapped[str] = mapped_column(String(60))
    situacao: Mapped[str] = mapped_column(String(20))
    valido_ate: Mapped[str] = mapped_column(String(10))
    dias_restantes: Mapped[int] = mapped_column(Integer, default=14)
    criado_em: Mapped[str] = mapped_column(String(30))
    usado_em: Mapped[str | None] = mapped_column(String(30))


class OfensivaClubeModel(Base):
    """Semanas seguidas em que o cliente abriu a carta (ofensiva do Clube Bulbe)."""

    __tablename__ = "ofensivas_clube"

    cliente_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("clientes.id", ondelete="CASCADE"), primary_key=True
    )
    semanas_sequencia: Mapped[int] = mapped_column(Integer, default=0)
