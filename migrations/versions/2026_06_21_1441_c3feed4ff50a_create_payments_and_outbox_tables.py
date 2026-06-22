"""create payments and outbox tables

Revision ID: c3feed4ff50a
Revises: 
Create Date: 2026-06-21 14:41:07.782428

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c3feed4ff50a'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('payments',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('amount', sa.Numeric(precision=18, scale=2), nullable=False),
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('idempotency_key', sa.String(length=255), nullable=False),
    sa.Column('request_hash', sa.String(length=64), nullable=False),
    sa.Column('webhook_url', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('idempotency_key')
    )
    op.create_table('outbox_events',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('aggregate_id', sa.Uuid(), nullable=False),
    sa.Column('event_type', sa.String(length=100), nullable=False),
    sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('published', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['aggregate_id'], ['payments.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_outbox_events_unpublished', 'outbox_events', ['published'], unique=False, postgresql_where='published = false')


def downgrade() -> None:
    op.drop_index('ix_outbox_events_unpublished', table_name='outbox_events', postgresql_where='published = false')
    op.drop_table('outbox_events')
    op.drop_table('payments')
