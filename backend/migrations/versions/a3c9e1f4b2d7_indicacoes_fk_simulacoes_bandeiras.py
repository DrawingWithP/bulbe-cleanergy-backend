"""indicacoes com FK para clientes, simulacoes com bandeira e tabela de bandeiras

- verificacoes_primeiro_acesso.codigo passa a VARCHAR(6), igual ao modelo
  (o codigo enviado ao cliente tem 6 digitos).
- indicacoes.cliente_id passa de INTEGER para o UUID do cliente (texto), com
  FK para clientes.id e ON DELETE CASCADE. Indicacoes que nao apontam para um
  cliente existente nao tem como ser associadas e sao removidas.
- simulacoes ganha cliente_id (opcional), bandeira, economia_mensal e
  economia_total (RF-03).
- nova tabela bandeiras_tarifarias (bandeira vigente por mes).

Revision ID: a3c9e1f4b2d7
Revises: 785415a75946
Create Date: 2026-11-15 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a3c9e1f4b2d7"
down_revision: Union[str, Sequence[str], None] = "785415a75946"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


FK_INDICACAO_CLIENTE = "fk_indicacoes_cliente_id_clientes"
FK_SIMULACAO_CLIENTE = "fk_simulacoes_cliente_id_clientes"


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("verificacoes_primeiro_acesso") as batch:
        batch.alter_column(
            "codigo",
            existing_type=sa.String(length=10),
            type_=sa.String(length=6),
            existing_nullable=False,
        )

    with op.batch_alter_table("indicacoes") as batch:
        batch.alter_column(
            "cliente_id",
            existing_type=sa.Integer(),
            type_=sa.String(length=36),
            existing_nullable=False,
            postgresql_using="cliente_id::text",
        )

    op.execute(
        "DELETE FROM indicacoes "
        "WHERE cliente_id NOT IN (SELECT id FROM clientes)"
    )

    with op.batch_alter_table("indicacoes") as batch:
        batch.create_foreign_key(
            FK_INDICACAO_CLIENTE,
            "clientes",
            ["cliente_id"],
            ["id"],
            ondelete="CASCADE",
        )

    with op.batch_alter_table("simulacoes") as batch:
        batch.add_column(
            sa.Column("cliente_id", sa.String(length=36), nullable=True)
        )
        batch.add_column(
            sa.Column(
                "bandeira",
                sa.String(length=20),
                nullable=False,
                server_default="verde",
            )
        )
        batch.add_column(
            sa.Column("economia_mensal", sa.Float(), nullable=True)
        )
        batch.add_column(
            sa.Column("economia_total", sa.Float(), nullable=True)
        )
        batch.create_index(
            "ix_simulacoes_cliente_id",
            ["cliente_id"],
            unique=False,
        )
        batch.create_foreign_key(
            FK_SIMULACAO_CLIENTE,
            "clientes",
            ["cliente_id"],
            ["id"],
            ondelete="SET NULL",
        )

    op.create_table(
        "bandeiras_tarifarias",
        sa.Column("mes_referencia", sa.String(length=7), nullable=False),
        sa.Column("bandeira", sa.String(length=20), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("mes_referencia"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("bandeiras_tarifarias")

    with op.batch_alter_table("simulacoes") as batch:
        batch.drop_constraint(FK_SIMULACAO_CLIENTE, type_="foreignkey")
        batch.drop_index("ix_simulacoes_cliente_id")
        batch.drop_column("economia_total")
        batch.drop_column("economia_mensal")
        batch.drop_column("bandeira")
        batch.drop_column("cliente_id")

    with op.batch_alter_table("indicacoes") as batch:
        batch.drop_constraint(FK_INDICACAO_CLIENTE, type_="foreignkey")

    # UUIDs nao cabem em INTEGER: as indicacoes sao descartadas no downgrade.
    op.execute("DELETE FROM indicacoes")

    with op.batch_alter_table("indicacoes") as batch:
        batch.alter_column(
            "cliente_id",
            existing_type=sa.String(length=36),
            type_=sa.Integer(),
            existing_nullable=False,
            postgresql_using="cliente_id::integer",
        )

    with op.batch_alter_table("verificacoes_primeiro_acesso") as batch:
        batch.alter_column(
            "codigo",
            existing_type=sa.String(length=6),
            type_=sa.String(length=10),
            existing_nullable=False,
        )
