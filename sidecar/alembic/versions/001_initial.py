"""Initial schema

Revision ID: 001_initial
Revises:
Create Date: 2024-02-13 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create projects table
    op.create_table(
        'projects',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('source_language', sa.String(length=10), nullable=False),
        sa.Column('target_language', sa.String(length=10), nullable=True),
        sa.Column('genre', sa.String(length=50), nullable=True),
        sa.Column('style_settings', sa.JSON(), nullable=True),
        sa.Column('pipeline_type', sa.String(length=30), nullable=False),
        sa.Column('llm_provider', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_projects_id'), 'projects', ['id'], unique=False)

    # Create chapters table
    op.create_table(
        'chapters',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('order', sa.Integer(), nullable=False),
        sa.Column('source_content', sa.Text(), nullable=True),
        sa.Column('file_path', sa.String(length=512), nullable=True),
        sa.Column('translated_content', sa.Text(), nullable=True),
        sa.Column('translation_stale', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_chapters_id'), 'chapters', ['id'], unique=False)

    # Create segments table
    op.create_table(
        'segments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('chapter_id', sa.Integer(), nullable=False),
        sa.Column('order', sa.Integer(), nullable=False),
        sa.Column('source_text', sa.Text(), nullable=False),
        sa.Column('source_start_offset', sa.Integer(), nullable=True),
        sa.Column('source_end_offset', sa.Integer(), nullable=True),
        sa.Column('translated_text', sa.Text(), nullable=True),
        sa.Column('status', sa.Enum('PENDING', 'TRANSLATING', 'TRANSLATED', 'REVIEWED', 'APPROVED', name='translationstatus'), nullable=False),
        sa.Column('speaker', sa.String(length=100), nullable=True),
        sa.Column('segment_type', sa.String(length=50), nullable=False),
        sa.Column('extra_data', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['chapter_id'], ['chapters.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_segments_id'), 'segments', ['id'], unique=False)
    op.create_index('ix_segments_chapter_order', 'segments', ['chapter_id', 'order'], unique=False)

    # Create translation_batches table
    op.create_table(
        'translation_batches',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('chapter_id', sa.Integer(), nullable=False),
        sa.Column('target_language', sa.String(length=10), nullable=False),
        sa.Column('batch_order', sa.Integer(), nullable=False),
        sa.Column('situation_summary', sa.Text(), nullable=True),
        sa.Column('character_events', sa.JSON(), nullable=True),
        sa.Column('full_cot_json', sa.JSON(), nullable=True),
        sa.Column('segment_ids', sa.JSON(), nullable=True),
        sa.Column('review_feedback', sa.JSON(), nullable=True),
        sa.Column('review_iteration', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['chapter_id'], ['chapters.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_translation_batches_id'), 'translation_batches', ['id'], unique=False)

    # Create translations table
    op.create_table(
        'translations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('segment_id', sa.Integer(), nullable=False),
        sa.Column('target_language', sa.String(length=10), nullable=False),
        sa.Column('translated_text', sa.Text(), nullable=True),
        sa.Column('translated_start_offset', sa.Integer(), nullable=True),
        sa.Column('translated_end_offset', sa.Integer(), nullable=True),
        sa.Column('manually_edited', sa.Boolean(), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'TRANSLATING', 'TRANSLATED', 'REVIEWED', 'APPROVED', name='translationstatus'), nullable=False),
        sa.Column('batch_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['batch_id'], ['translation_batches.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['segment_id'], ['segments.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('segment_id', 'target_language', name='uq_translation_segment_lang')
    )
    op.create_index(op.f('ix_translations_id'), 'translations', ['id'], unique=False)
    op.create_index('ix_translations_segment_lang', 'translations', ['segment_id', 'target_language'], unique=False)

    # Create glossary_entries table
    op.create_table(
        'glossary_entries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('source_term', sa.String(length=255), nullable=False),
        sa.Column('translated_term', sa.String(length=255), nullable=False),
        sa.Column('term_type', sa.String(length=50), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('context', sa.Text(), nullable=True),
        sa.Column('auto_detected', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_glossary_entries_id'), 'glossary_entries', ['id'], unique=False)
    op.create_index('ix_glossary_project_term', 'glossary_entries', ['project_id', 'source_term'], unique=False)

    # Create personas table
    op.create_table(
        'personas',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('aliases', sa.JSON(), nullable=True),
        sa.Column('personality', sa.Text(), nullable=True),
        sa.Column('speech_style', sa.Text(), nullable=True),
        sa.Column('formality_level', sa.Integer(), nullable=False),
        sa.Column('age_group', sa.String(length=50), nullable=True),
        sa.Column('example_dialogues', sa.JSON(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('auto_detected', sa.Boolean(), nullable=False),
        sa.Column('detection_confidence', sa.Float(), nullable=True),
        sa.Column('source_chapter_id', sa.Integer(), nullable=True),
        sa.Column('appearance_count', sa.Integer(), nullable=False),
        sa.Column('last_seen_chapter_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['last_seen_chapter_id'], ['chapters.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_chapter_id'], ['chapters.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_personas_id'), 'personas', ['id'], unique=False)

    # Create persona_suggestions table
    op.create_table(
        'persona_suggestions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('persona_id', sa.Integer(), nullable=False),
        sa.Column('field_name', sa.String(length=50), nullable=False),
        sa.Column('suggested_value', sa.Text(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('source_batch_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['persona_id'], ['personas.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_batch_id'], ['translation_batches.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_persona_suggestions_id'), 'persona_suggestions', ['id'], unique=False)

    # Create pipeline_runs table
    op.create_table(
        'pipeline_runs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('chapter_id', sa.Integer(), nullable=False),
        sa.Column('target_language', sa.String(length=10), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED', name='pipelinestatus'), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('config', sa.JSON(), nullable=True),
        sa.Column('stats', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['chapter_id'], ['chapters.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_pipeline_runs_id'), 'pipeline_runs', ['id'], unique=False)
    op.create_index('ix_pipeline_runs_chapter_status', 'pipeline_runs', ['chapter_id', 'status'], unique=False)

    # Create exports table
    op.create_table(
        'exports',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('chapter_id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('format', sa.String(length=10), nullable=False),
        sa.Column('file_path', sa.String(length=512), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['chapter_id'], ['chapters.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_exports_id'), 'exports', ['id'], unique=False)
    op.create_index('ix_exports_chapter_format', 'exports', ['chapter_id', 'format'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index('ix_exports_chapter_format', table_name='exports')
    op.drop_index(op.f('ix_exports_id'), table_name='exports')
    op.drop_table('exports')

    op.drop_index('ix_pipeline_runs_chapter_status', table_name='pipeline_runs')
    op.drop_index(op.f('ix_pipeline_runs_id'), table_name='pipeline_runs')
    op.drop_table('pipeline_runs')

    op.drop_index(op.f('ix_persona_suggestions_id'), table_name='persona_suggestions')
    op.drop_table('persona_suggestions')

    op.drop_index(op.f('ix_personas_id'), table_name='personas')
    op.drop_table('personas')

    op.drop_index('ix_glossary_project_term', table_name='glossary_entries')
    op.drop_index(op.f('ix_glossary_entries_id'), table_name='glossary_entries')
    op.drop_table('glossary_entries')

    op.drop_index('ix_translations_segment_lang', table_name='translations')
    op.drop_index(op.f('ix_translations_id'), table_name='translations')
    op.drop_table('translations')

    op.drop_index(op.f('ix_translation_batches_id'), table_name='translation_batches')
    op.drop_table('translation_batches')

    op.drop_index('ix_segments_chapter_order', table_name='segments')
    op.drop_index(op.f('ix_segments_id'), table_name='segments')
    op.drop_table('segments')

    op.drop_index(op.f('ix_chapters_id'), table_name='chapters')
    op.drop_table('chapters')

    op.drop_index(op.f('ix_projects_id'), table_name='projects')
    op.drop_table('projects')
