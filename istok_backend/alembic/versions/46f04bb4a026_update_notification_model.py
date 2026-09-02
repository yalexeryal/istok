import sqlalchemy as sa
from alembic import op


def upgrade() -> None:
    # 1. Добавляем колонку как nullable (чтобы не ломать существующие строки)
    op.add_column('notifications', sa.Column('message', sa.String(length=500), nullable=True))

    # 2. Заполняем все существующие строки значением по умолчанию
    op.execute("UPDATE notifications SET message = 'Новое уведомление' WHERE message IS NULL")

    # 3. Теперь безопасно делаем колонку NOT NULL
    op.alter_column('notifications', 'message', nullable=False)

    # Если в миграции также добавлялась колонка payload, добавляем её (она может быть nullable)
    # op.add_column('notifications', sa.Column('payload', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('notifications', 'message')
    # op.drop_column('notifications', 'payload')