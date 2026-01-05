"""Add noshow_predictions table for ML-powered no-show prediction

Revision ID: 009_add_noshow_predictions
Revises: 008_add_health_records
Create Date: 2026-01-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '009_add_noshow_predictions'
down_revision: Union[str, None] = '008_add_health_records'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # NoShow predictions table
    op.create_table(
        'noshow_predictions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),

        # Appointment relationship (unique - one prediction per appointment)
        sa.Column(
            'appointment_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('appointments.id', ondelete='CASCADE'),
            nullable=False,
            unique=True,
        ),

        # Prediction results
        sa.Column('probability', sa.Float, nullable=False),
        sa.Column('risk_level', sa.String(20), nullable=False),

        # Prediction metadata
        sa.Column('features_used', postgresql.JSONB, nullable=False),
        sa.Column('model_version', sa.String(50), nullable=False, server_default='1.0.0'),
        sa.Column('predicted_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),

        # Outcome tracking (for model improvement)
        sa.Column('was_accurate', sa.Boolean, nullable=True),
        sa.Column('actual_outcome', sa.String(20), nullable=True),
        sa.Column('feedback_recorded_at', sa.DateTime(timezone=True), nullable=True),

        # Mitigation recommendations
        sa.Column('mitigation_actions', postgresql.JSONB, nullable=True),
    )

    # Create indexes for efficient querying
    op.create_index('ix_noshow_predictions_appointment_id', 'noshow_predictions', ['appointment_id'])
    op.create_index('ix_noshow_predictions_risk_level', 'noshow_predictions', ['risk_level'])
    op.create_index('ix_noshow_predictions_predicted_at', 'noshow_predictions', ['predicted_at'])

    # Composite index for finding high-risk predictions
    op.create_index(
        'ix_noshow_predictions_risk_probability',
        'noshow_predictions',
        ['risk_level', 'probability']
    )

    # Composite index for model performance analysis
    op.create_index(
        'ix_noshow_predictions_outcome_accuracy',
        'noshow_predictions',
        ['actual_outcome', 'was_accurate']
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_noshow_predictions_outcome_accuracy')
    op.drop_index('ix_noshow_predictions_risk_probability')
    op.drop_index('ix_noshow_predictions_predicted_at')
    op.drop_index('ix_noshow_predictions_risk_level')
    op.drop_index('ix_noshow_predictions_appointment_id')

    # Drop table
    op.drop_table('noshow_predictions')
