"""add_performance_indexes

Revision ID: bb5fd9cbc059
Revises: eba0f3eeb2c8
Create Date: 2026-09-02 20:00:15.364603

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = 'bb5fd9cbc059'
down_revision: Union[str, None] = 'eba0f3eeb2c8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Индексы для ускорения поиска персон (GIN с pg_trgm)
    op.execute("CREATE INDEX IF NOT EXISTS idx_persons_last_name ON persons USING gin (last_name gin_trgm_ops)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_persons_first_name ON persons USING gin (first_name gin_trgm_ops)")

    # Индекс для быстрого поиска по дате рождения
    op.execute("CREATE INDEX IF NOT EXISTS idx_persons_birth_date ON persons (birth_date)")

    # Индексы для связей дерево-персона
    op.execute("CREATE INDEX IF NOT EXISTS idx_tree_person_tree_id ON tree_persons (tree_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_tree_person_person_id ON tree_persons (person_id)")

    # Индексы для запросов на доступ
    op.execute("CREATE INDEX IF NOT EXISTS idx_access_requests_tree_id ON access_requests (tree_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_access_requests_requester_id ON access_requests (requester_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_access_requests_status ON access_requests (status)")

    # Индексы для уведомлений
    op.execute("CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_notifications_is_read ON notifications (is_read)")

    # Индекс для деревьев
    op.execute("CREATE INDEX IF NOT EXISTS idx_trees_owner_id ON trees (owner_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_persons_last_name")
    op.execute("DROP INDEX IF EXISTS idx_persons_first_name")
    op.execute("DROP INDEX IF EXISTS idx_persons_birth_date")
    op.execute("DROP INDEX IF EXISTS idx_tree_person_tree_id")
    op.execute("DROP INDEX IF EXISTS idx_tree_person_person_id")
    op.execute("DROP INDEX IF EXISTS idx_access_requests_tree_id")
    op.execute("DROP INDEX IF EXISTS idx_access_requests_requester_id")
    op.execute("DROP INDEX IF EXISTS idx_access_requests_status")
    op.execute("DROP INDEX IF EXISTS idx_notifications_user_id")
    op.execute("DROP INDEX IF EXISTS idx_notifications_is_read")
    op.execute("DROP INDEX IF EXISTS idx_trees_owner_id")