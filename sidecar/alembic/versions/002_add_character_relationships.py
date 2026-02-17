"""Add character relationships table

Revision ID: 002_add_character_relationships
Revises: 001_initial
Create Date: 2024-02-17 00:00:00.000000

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = '002_add_character_relationships'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'character_relationships',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('persona_id_1', sa.Integer(), nullable=False),
        sa.Column('persona_id_2', sa.Integer(), nullable=False),
        sa.Column('relationship_type', sa.String(length=50), nullable=False, server_default='acquaintance'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('intimacy_level', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('auto_detected', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('detection_confidence', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['persona_id_1'], ['personas.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['persona_id_2'], ['personas.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('persona_id_1', 'persona_id_2', name='uq_relationship_pair'),
    )
    op.create_index(op.f('ix_character_relationships_id'), 'character_relationships', ['id'], unique=False)
    op.create_index('ix_relationships_project', 'character_relationships', ['project_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_relationships_project', table_name='character_relationships')
    op.drop_index(op.f('ix_character_relationships_id'), table_name='character_relationships')
    op.drop_table('character_relationships')
