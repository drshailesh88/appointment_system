"""Add documents table for Phase 10: Document Scanner & OCR.

Revision ID: 005_add_documents
Revises: 004_add_procedures
Create Date: 2026-01-04 14:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "005_add_documents"
down_revision: Union[str, None] = "004_add_procedures"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create documents table."""
    op.create_table(
        "documents",
        # Primary Key (UUID)
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        # Foreign Keys
        sa.Column(
            "clinic_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clinics.id"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "patient_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("patients.id"),
            nullable=False,
            index=True,
        ),
        # File Information
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("file_type", sa.String(100), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("file_size", sa.Integer, nullable=True),
        sa.Column("page_count", sa.Integer, nullable=False, server_default="1"),
        # Document Classification
        sa.Column(
            "document_type",
            sa.String(50),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "scan_date",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            index=True,
        ),
        # OCR Data
        sa.Column("is_processed", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("ocr_text", sa.Text, nullable=True),
        sa.Column("ocr_language", sa.String(50), nullable=True),
        sa.Column("ocr_confidence", sa.Float, nullable=True),
        # Extracted Structured Data (JSON)
        sa.Column("extracted_data", postgresql.JSONB, nullable=True),
        # Tags and Notes
        sa.Column("tags", postgresql.JSONB, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        # EMR Integration
        sa.Column(
            "emr_document_id",
            sa.String(50),
            nullable=True,
            index=True,
        ),
        sa.Column("synced_to_emr", sa.Boolean, nullable=False, server_default="false"),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )

    # Create indexes for better query performance
    op.create_index(
        "idx_documents_clinic_patient",
        "documents",
        ["clinic_id", "patient_id"],
    )
    op.create_index(
        "idx_documents_clinic_type",
        "documents",
        ["clinic_id", "document_type"],
    )
    op.create_index(
        "idx_documents_clinic_processed",
        "documents",
        ["clinic_id", "is_processed"],
    )


def downgrade() -> None:
    """Drop documents table."""
    op.drop_index("idx_documents_clinic_processed", table_name="documents")
    op.drop_index("idx_documents_clinic_type", table_name="documents")
    op.drop_index("idx_documents_clinic_patient", table_name="documents")
    op.drop_table("documents")
