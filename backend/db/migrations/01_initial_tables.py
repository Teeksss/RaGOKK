# Last reviewed: 2025-04-29 11:15:42 UTC (User: TeeksssPDF)
"""
Initial database tables

Revision ID: 01_initial_tables
Create Date: 2025-04-29 11:15:42.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = '01_initial_tables'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(), nullable=True),
        sa.Column('email', sa.String(), nullable=True),
        sa.Column('hashed_password', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('is_admin', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    
    # documents table
    op.create_table(
        'documents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('metadata', sa.Text(), nullable=True),
        sa.Column('owner_id', sa.String(), nullable=True),
        sa.Column('source_url', sa.String(), nullable=True),
        sa.Column('source_type', sa.String(), nullable=True),
        sa.Column('is_processed', sa.Boolean(), nullable=True),
        sa.Column('is_public', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_viewed', sa.DateTime(timezone=True), nullable=True),
        sa.Column('view_count', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_documents_created_at'), 'documents', ['created_at'], unique=False)
    op.create_index(op.f('ix_documents_id'), 'documents', ['id'], unique=False)
    op.create_index(op.f('ix_documents_owner_id'), 'documents', ['owner_id'], unique=False)
    op.create_index(op.f('ix_documents_source_type'), 'documents', ['source_type'], unique=False)
    op.create_index(op.f('ix_documents_title'), 'documents', ['title'], unique=False)
    op.create_index(op.f('ix_documents_updated_at'), 'documents', ['updated_at'], unique=False)
    
    # document_versions table
    op.create_table(
        'document_versions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('metadata', sa.Text(), nullable=True),
        sa.Column('version_label', sa.String(), nullable=True),
        sa.Column('created_by', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('change_description', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_document_versions_created_at'), 'document_versions', ['created_at'], unique=False)
    op.create_index(op.f('ix_document_versions_document_id'), 'document_versions', ['document_id'], unique=False)
    op.create_index(op.f('ix_document_versions_id'), 'document_versions', ['id'], unique=False)
    op.create_index(op.f('ix_document_versions_version_label'), 'document_versions', ['version_label'], unique=False)
    
    # document_tags table
    op.create_table(
        'document_tags',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=True),
        sa.Column('tag_name', sa.String(), nullable=True),
        sa.Column('created_by', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_document_tags_document_id'), 'document_tags', ['document_id'], unique=False)
    op.create_index(op.f('ix_document_tags_id'), 'document_tags', ['id'], unique=False)
    op.create_index(op.f('ix_document_tags_tag_name'), 'document_tags', ['tag_name'], unique=False)
    
    # user_document_permissions table
    op.create_table(
        'user_document_permissions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=True),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.Column('permission_type', sa.String(), nullable=True),
        sa.Column('granted_by', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_document_permissions_document_id'), 'user_document_permissions', ['document_id'], unique=False)
    op.create_index(op.f('ix_user_document_permissions_id'), 'user_document_permissions', ['id'], unique=False)
    op.create_index(op.f('ix_user_document_permissions_user_id'), 'user_document_permissions', ['user_id'], unique=False)
    
    # document_embeddings table
    op.create_table(
        'document_embeddings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=True),
        sa.Column('chunk_id', sa.String(), nullable=True),
        sa.Column('chunk_text', sa.Text(), nullable=True),
        sa.Column('embedding', sa.Text(), nullable=True),
        sa.Column('embedding_model', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_document_embeddings_chunk_id'), 'document_embeddings', ['chunk_id'], unique=False)
    op.create_index(op.f('ix_document_embeddings_document_id'), 'document_embeddings', ['document_id'], unique=False)
    op.create_index(op.f('ix_document_embeddings_id'), 'document_embeddings', ['id'], unique=False)
    
    # document_syncs table
    op.create_table(
        'document_syncs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source_path', sa.String(), nullable=True),
        sa.Column('document_id', sa.Integer(), nullable=True),
        sa.Column('last_sync_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_modified_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('hash_value', sa.String(), nullable=True),
        sa.Column('sync_status', sa.String(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_document_syncs_document_id'), 'document_syncs', ['document_id'], unique=False)
    op.create_index(op.f('ix_document_syncs_id'), 'document_syncs', ['id'], unique=False)
    op.create_index(op.f('ix_document_syncs_source_path'), 'document_syncs', ['source_path'], unique=True)


def downgrade():
    op.drop_table('document_syncs')
    op.drop_table('document_embeddings')
    op.drop_table('user_document_permissions')
    op.drop_table('document_tags')
    op.drop_table('document_versions')
    op.drop_table('documents')
    op.drop_table('users')