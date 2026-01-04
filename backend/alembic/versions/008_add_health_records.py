"""Add health_records table for Apple Health integration

Revision ID: 008_add_health_records
Revises: 007_add_lab_results
Create Date: 2026-01-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '008_add_health_records'
down_revision: Union[str, None] = '007_add_lab_results'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Health records table
    op.create_table(
        'health_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),

        # Patient relationship
        sa.Column(
            'patient_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('patients.id', ondelete='CASCADE'),
            nullable=False,
        ),

        # Metric information
        sa.Column('metric_type', sa.String(50), nullable=False),
        sa.Column('value', sa.Numeric(10, 2), nullable=False),
        sa.Column('unit', sa.String(20), nullable=False),

        # Timing
        sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False),

        # Source information
        sa.Column('source', sa.String(100), nullable=False, server_default='manual'),
        sa.Column('device_id', sa.String(100), nullable=True),

        # Additional data
        sa.Column('metadata', postgresql.JSON, nullable=True),
    )

    # Create indexes for efficient querying
    op.create_index('ix_health_records_patient_id', 'health_records', ['patient_id'])
    op.create_index('ix_health_records_metric_type', 'health_records', ['metric_type'])
    op.create_index('ix_health_records_recorded_at', 'health_records', ['recorded_at'])

    # Composite index for patient + metric type + time (most common query)
    op.create_index(
        'ix_health_records_patient_metric_time',
        'health_records',
        ['patient_id', 'metric_type', 'recorded_at']
    )

    # Composite index for patient + time (for summaries)
    op.create_index(
        'ix_health_records_patient_time',
        'health_records',
        ['patient_id', 'recorded_at']
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_health_records_patient_time')
    op.drop_index('ix_health_records_patient_metric_time')
    op.drop_index('ix_health_records_recorded_at')
    op.drop_index('ix_health_records_metric_type')
    op.drop_index('ix_health_records_patient_id')

    # Drop table
    op.drop_table('health_records')
