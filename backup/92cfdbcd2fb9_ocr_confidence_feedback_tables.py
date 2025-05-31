"""ocr confidence feedback tables

Revision ID: 92cfdbcd2fb9
Revises: fae191b3aff9
Create Date: 2025-04-13 09:56:43.714654

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '92cfdbcd2fb9'
down_revision: Union[str, None] = 'fae191b3aff9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create ocr_confidence table
    op.create_table(
        'ocr_confidence',
        sa.Column('ocr_confidence_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('ocr_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('field_name', sa.String(), nullable=False),
        sa.Column('confidence_score', sa.Numeric(precision=3, scale=2), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['ocr_id'], ['ocr_results.ocr_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('ocr_confidence_id')
    )
    
    # Create ocr_training_feedback table
    op.create_table(
        'ocr_training_feedback',
        sa.Column('feedback_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('ocr_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('field_name', sa.String(), nullable=False),
        sa.Column('original_value', sa.String(), nullable=False),
        sa.Column('corrected_value', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['ocr_id'], ['ocr_results.ocr_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('feedback_id')
    )


def downgrade() -> None:
    op.drop_table('ocr_training_feedback')
    op.drop_table('ocr_confidence')
