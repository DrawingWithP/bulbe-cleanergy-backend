"""dicas: icone pronto e vitrine do app

- dicas.icone (lista fechada, padrao lampada_led);
- dicas.em_exibicao e dicas.ordem (as 5 dicas do carrossel do app);
- dicas.imagem_svg passa a ser opcional (obsoleto: o app usa o icone).

Revision ID: d9f1b3c5e7a2
Revises: c4e8a2b6d1f5
Create Date: 2026-11-15 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d9f1b3c5e7a2"
down_revision: Union[str, Sequence[str], None] = "c4e8a2b6d1f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("dicas") as batch:
        batch.add_column(sa.Column("icone", sa.String(length=30), nullable=False, server_default="lampada_led"))
        batch.add_column(sa.Column("em_exibicao", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.add_column(sa.Column("ordem", sa.Integer(), nullable=True))
        batch.alter_column("imagem_svg", existing_type=sa.Text(), nullable=True)


def downgrade() -> None:
    op.execute("UPDATE dicas SET imagem_svg = '<svg/>' WHERE imagem_svg IS NULL")
    with op.batch_alter_table("dicas") as batch:
        batch.alter_column("imagem_svg", existing_type=sa.Text(), nullable=False)
        batch.drop_column("ordem")
        batch.drop_column("em_exibicao")
        batch.drop_column("icone")
