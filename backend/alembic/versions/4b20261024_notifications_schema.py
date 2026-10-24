"""notifications_schema

Revision ID: 4b20261024
Revises: 30420276a191
Create Date: 2026-10-24 07:48:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '4b20261024'
down_revision: Union[str, Sequence[str], None] = '30420276a191'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. Create notifications table
    op.create_table(
        'notifications',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('rule', sa.String(length=64), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('tags', sa.String(length=255), nullable=True),
        sa.Column('event_ref', sa.String(length=100), nullable=False),
        sa.Column('dedup_key', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='pending'),
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('dedup_key', name='uq_notifications_dedup_key')
    )
    op.create_index('ix_notifications_rule', 'notifications', ['rule'])
    op.create_index('ix_notifications_event_ref', 'notifications', ['event_ref'])
    op.create_index('ix_notifications_status', 'notifications', ['status'])

    # 2. Create notification_settings table
    op.create_table(
        'notification_settings',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('owner_id', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('rule', sa.String(length=64), nullable=False),
        sa.Column('enabled', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('threshold', sa.Float(), nullable=False, server_default='10.0'),
        sa.Column('quiet_hours_start', sa.String(length=5), nullable=False, server_default='22:00'),
        sa.Column('quiet_hours_end', sa.String(length=5), nullable=False, server_default='07:00'),
        sa.Column('min_minutes_between', sa.Integer(), nullable=False, server_default='60'),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('owner_id', 'rule', name='uq_owner_rule_setting')
    )
    op.create_index('ix_notification_settings_rule', 'notification_settings', ['rule'])
    op.create_index('ix_notification_settings_owner_id', 'notification_settings', ['owner_id'])

def downgrade() -> None:
    op.drop_index('ix_notification_settings_owner_id', table_name='notification_settings')
    op.drop_index('ix_notification_settings_rule', table_name='notification_settings')
    op.drop_table('notification_settings')
    op.drop_index('ix_notifications_status', table_name='notifications')
    op.drop_index('ix_notifications_event_ref', table_name='notifications')
    op.drop_index('ix_notifications_rule', table_name='notifications')
    op.drop_table('notifications')
