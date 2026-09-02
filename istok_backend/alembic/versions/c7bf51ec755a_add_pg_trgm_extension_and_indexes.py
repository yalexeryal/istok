"""add_pg_trgm_extension_and_indexes

Revision ID: c7bf51ec755a
Revises: 56510abdb07f
Create Date: 2026-08-05 17:35:50.296965

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7bf51ec755a'
down_revision: Union[str, Sequence[str], None] = '56510abdb07f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Включаем расширение pg_trgm для триграммного поиска
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")

    # Создаем GIN-индексы для быстрого нечеткого поиска
    op.create_index(
        "ix_persons_first_name_trgm",
        "persons",
        ["first_name"],
        postgresql_using="gin",
        postgresql_ops={"first_name": "gin_trgm_ops"}
    )
    op.create_index(
        "ix_persons_last_name_trgm",
        "persons",
        ["last_name"],
        postgresql_using="gin",
        postgresql_ops={"last_name": "gin_trgm_ops"}
    )
    op.create_index(
        "ix_persons_middle_name_trgm",
        "persons",
        ["middle_name"],
        postgresql_using="gin",
        postgresql_ops={"middle_name": "gin_trgm_ops"}
    )


def downgrade() -> None:
    op.drop_index("ix_persons_middle_name_trgm", table_name="persons")
    op.drop_index("ix_persons_last_name_trgm", table_name="persons")
    op.drop_index("ix_persons_first_name_trgm", table_name="persons")
    op.execute("DROP EXTENSION IF EXISTS pg_trgm;")
