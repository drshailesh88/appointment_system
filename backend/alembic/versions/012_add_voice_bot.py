"""Add voice bot and phone calls

Revision ID: 012
Revises: 011
Create Date: 2026-01-05

Phase 18: Voice Bot / Phone Automation
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add phone calls and voice bot tables."""
    # Create phone_calls table
    op.create_table(
        "phone_calls",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("call_sid", sa.String(length=100), nullable=False),
        sa.Column("from_number", sa.String(length=20), nullable=False),
        sa.Column("to_number", sa.String(length=20), nullable=False),
        sa.Column("direction", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("session_id", sa.String(length=100), nullable=True),
        sa.Column("transcript", sa.Text(), nullable=True),
        sa.Column("intent_detected", sa.String(length=100), nullable=True),
        sa.Column("action_taken", sa.String(length=100), nullable=True),
        sa.Column("appointment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("language_detected", sa.String(length=20), nullable=True),
        sa.Column("sentiment", sa.String(length=20), nullable=True),
        sa.Column("recording_url", sa.String(length=500), nullable=True),
        sa.Column("recording_consent", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["appointment_id"],
            ["appointments.id"],
            name=op.f("fk_phone_calls_appointment_id_appointments"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
            name=op.f("fk_phone_calls_patient_id_patients"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name=op.f("fk_phone_calls_clinic_id_clinics"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_phone_calls")),
        sa.UniqueConstraint("call_sid", name=op.f("uq_phone_calls_call_sid")),
    )
    op.create_index(
        op.f("ix_phone_calls_call_sid"),
        "phone_calls",
        ["call_sid"],
        unique=False,
    )
    op.create_index(
        op.f("ix_phone_calls_clinic_id"),
        "phone_calls",
        ["clinic_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_phone_calls_patient_id"),
        "phone_calls",
        ["patient_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_phone_calls_status"),
        "phone_calls",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_phone_calls_direction"),
        "phone_calls",
        ["direction"],
        unique=False,
    )
    op.create_index(
        op.f("ix_phone_calls_created_at"),
        "phone_calls",
        ["created_at"],
        unique=False,
    )

    # Create call_transcript_segments table
    op.create_table(
        "call_transcript_segments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("call_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("speaker", sa.String(length=20), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("language", sa.String(length=10), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("start_time_ms", sa.Integer(), nullable=False),
        sa.Column("end_time_ms", sa.Integer(), nullable=False),
        sa.Column("entities", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["call_id"],
            ["phone_calls.id"],
            name=op.f("fk_call_transcript_segments_call_id_phone_calls"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_call_transcript_segments")),
    )
    op.create_index(
        op.f("ix_call_transcript_segments_call_id"),
        "call_transcript_segments",
        ["call_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_call_transcript_segments_speaker"),
        "call_transcript_segments",
        ["speaker"],
        unique=False,
    )


def downgrade() -> None:
    """Drop phone calls and voice bot tables."""
    # Drop indexes
    op.drop_index(op.f("ix_call_transcript_segments_speaker"), table_name="call_transcript_segments")
    op.drop_index(op.f("ix_call_transcript_segments_call_id"), table_name="call_transcript_segments")
    op.drop_index(op.f("ix_phone_calls_created_at"), table_name="phone_calls")
    op.drop_index(op.f("ix_phone_calls_direction"), table_name="phone_calls")
    op.drop_index(op.f("ix_phone_calls_status"), table_name="phone_calls")
    op.drop_index(op.f("ix_phone_calls_patient_id"), table_name="phone_calls")
    op.drop_index(op.f("ix_phone_calls_clinic_id"), table_name="phone_calls")
    op.drop_index(op.f("ix_phone_calls_call_sid"), table_name="phone_calls")

    # Drop tables
    op.drop_table("call_transcript_segments")
    op.drop_table("phone_calls")
