"""Add categories and budgets

Revision ID: cb8df3a5e1ad
Revises: 47885b54861e
Create Date: 2025-04-05

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision = 'cb8df3a5e1ad'
down_revision = '47885b54861e'
branch_labels = None
depends_on = None


def upgrade():
    # Create categories table
    op.create_table(
        'categories',
        sa.Column('category_id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('icon', sa.String(), nullable=False),
        sa.Column('color', sa.String(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(), default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('category_id')
    )

    # Create user_categories table
    op.create_table(
        'user_categories',
        sa.Column('user_category_id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('icon', sa.String(), nullable=False),
        sa.Column('color', sa.String(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(), default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ),
        sa.PrimaryKeyConstraint('user_category_id')
    )

    # Create budgets table
    op.create_table(
        'budgets',
        sa.Column('budget_id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('category_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('user_category_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('period', sa.String(), nullable=False),
        sa.Column('month', sa.Integer(), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(), default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ),
        sa.ForeignKeyConstraint(['category_id'], ['categories.category_id'], ),
        sa.ForeignKeyConstraint(['user_category_id'], ['user_categories.user_category_id'], ),
        sa.PrimaryKeyConstraint('budget_id')
    )

    # Add columns to expense_items table
    op.add_column('expense_items', sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('expense_items', sa.Column('purchase_date', sa.Date(), nullable=True))
    
    # Create foreign key constraints for expense_items
    op.create_foreign_key('fk_expense_items_user_id', 'expense_items', 'users', ['user_id'], ['user_id'])

    # Add default categories
    op.execute("""
    INSERT INTO categories (category_id, name, icon, color)
    VALUES 
        (gen_random_uuid(), 'General', 'general', '#4CAF50'),
        (gen_random_uuid(), 'Groceries', 'shopping-cart', '#4CAF50'),
        (gen_random_uuid(), 'Dining', 'utensils', '#FF9800'),
        (gen_random_uuid(), 'Transportation', 'car', '#2196F3'),
        (gen_random_uuid(), 'Utilities', 'bolt', '#FFC107'),
        (gen_random_uuid(), 'Housing', 'home', '#795548'),
        (gen_random_uuid(), 'Entertainment', 'film', '#9C27B0'),
        (gen_random_uuid(), 'Health', 'heart', '#F44336'),
        (gen_random_uuid(), 'Shopping', 'shopping-bag', '#3F51B5'),
        (gen_random_uuid(), 'Travel', 'plane', '#009688'),
        (gen_random_uuid(), 'Education', 'book', '#607D8B'),
        (gen_random_uuid(), 'Personal Care', 'user', '#E91E63'),
        (gen_random_uuid(), 'Miscellaneous', 'ellipsis-h', '#9E9E9E'),
    """)


def downgrade():
    # Drop foreign key constraints
    op.drop_constraint('fk_expense_items_user_id', 'expense_items', type_='foreignkey')
    
    # Drop added columns from expense_items
    op.drop_column('expense_items', 'purchase_date')
    op.drop_column('expense_items', 'user_id')
    
    # Drop tables
    op.drop_table('budgets')
    op.drop_table('user_categories')
    op.drop_table('categories')
