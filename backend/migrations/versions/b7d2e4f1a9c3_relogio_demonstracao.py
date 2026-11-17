"""relogio de demonstracao

Tabela com o deslocamento do relogio usado na apresentacao (pular dias).

Revision ID: b7d2e4f1a9c3
Revises: a3c9e1f4b2d7
Create Date: 2026-11-15 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7d2e4f1a9c3"
down_revision: Union[str, Sequence[str], None] = "a3c9e1f4b2d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "relogio_demonstracao",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("deslocamento_segundos", sa.Integer(), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("relogio_demonstracao")
