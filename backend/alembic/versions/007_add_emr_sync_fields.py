"""Add EMR sync fields for Phase 13

Revision ID: 007_add_emr_sync_fields
Revises: 006_add_google_calendar_sync
Create Date: 2026-01-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '007_add_emr_sync_fields'
down_revision: Union[str, None] = '006_add_google_calendar_sync'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add EMR sync timestamp to patients table."""
    # Add emr_synced_at column to patients table
    op.add_column(
        'patients',
        sa.Column('emr_synced_at', sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    """Remove EMR sync fields."""
    op.drop_column('patients', 'emr_synced_at')
