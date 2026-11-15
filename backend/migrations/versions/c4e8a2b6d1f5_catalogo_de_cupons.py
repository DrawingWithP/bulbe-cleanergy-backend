"""catalogo de cupons do Clube Bulbe

- nova tabela cupons_catalogo (modelos de cupom por parceiro, sorteados nas
  cartas normais);
- cupons.modelo_id: modelo que gerou o cupom (copia, sem FK).

Revision ID: c4e8a2b6d1f5
Revises: b7d2e4f1a9c3
Create Date: 2026-11-15 15:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c4e8a2b6d1f5"
down_revision: Union[str, Sequence[str], None] = "b7d2e4f1a9c3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cupons_catalogo",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("parceiro_id", sa.String(length=36), nullable=False),
        sa.Column("titulo", sa.String(length=120), nullable=False),
        sa.Column("descricao", sa.String(length=300), nullable=False),
        sa.Column("tag", sa.String(length=60), nullable=False),
        sa.Column("prefixo_codigo", sa.String(length=12), nullable=False),
        sa.Column("validade_dias", sa.Integer(), nullable=False),
        sa.Column("peso", sa.Integer(), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False),
        sa.Column("criado_em", sa.String(length=30), nullable=False),
        sa.Column("atualizado_em", sa.String(length=30), nullable=True),
        sa.ForeignKeyConstraint(["parceiro_id"], ["parceiros.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cupons_catalogo_parceiro_id", "cupons_catalogo", ["parceiro_id"], unique=False)

    with op.batch_alter_table("cupons") as batch:
        batch.add_column(sa.Column("modelo_id", sa.String(length=36), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("cupons") as batch:
        batch.drop_column("modelo_id")

    op.drop_index("ix_cupons_catalogo_parceiro_id", table_name="cupons_catalogo")
    op.drop_table("cupons_catalogo")
