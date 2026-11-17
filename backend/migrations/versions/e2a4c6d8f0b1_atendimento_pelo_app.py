"""atendimento pelo app (chat com robo e atendente)

Tabelas atendimentos e atendimento_mensagens.

Revision ID: e2a4c6d8f0b1
Revises: d9f1b3c5e7a2
Create Date: 2026-11-15 16:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e2a4c6d8f0b1"
down_revision: Union[str, Sequence[str], None] = "d9f1b3c5e7a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "atendimentos",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("cliente_id", sa.String(length=36), nullable=False),
        sa.Column("assunto", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("atendente_nome", sa.String(length=100), nullable=True),
        sa.Column("avaliacao", sa.Integer(), nullable=True),
        sa.Column("criado_em", sa.String(length=30), nullable=False),
        sa.Column("atualizado_em", sa.String(length=30), nullable=False),
        sa.Column("encerrado_em", sa.String(length=30), nullable=True),
        sa.ForeignKeyConstraint(["cliente_id"], ["clientes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_atendimentos_cliente_id", "atendimentos", ["cliente_id"], unique=False)
    op.create_index("ix_atendimentos_status", "atendimentos", ["status"], unique=False)

    op.create_table(
        "atendimento_mensagens",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("atendimento_id", sa.String(length=36), nullable=False),
        sa.Column("autor", sa.String(length=20), nullable=False),
        sa.Column("texto", sa.Text(), nullable=False),
        sa.Column("opcoes", sa.JSON(), nullable=True),
        sa.Column("criado_em", sa.String(length=30), nullable=False),
        sa.ForeignKeyConstraint(["atendimento_id"], ["atendimentos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_atendimento_mensagens_atendimento_id", "atendimento_mensagens", ["atendimento_id"],
                    unique=False)


def downgrade() -> None:
    op.drop_index("ix_atendimento_mensagens_atendimento_id", table_name="atendimento_mensagens")
    op.drop_table("atendimento_mensagens")
    op.drop_index("ix_atendimentos_status", table_name="atendimentos")
    op.drop_index("ix_atendimentos_cliente_id", table_name="atendimentos")
    op.drop_table("atendimentos")
