from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'b167118927ca'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('email_hash', sa.String(length=64), nullable=True),
    sa.Column('email_encrypted', sa.String(length=500), nullable=True),
    sa.Column('username_hash', sa.String(length=64), nullable=True),
    sa.Column('username_encrypted', sa.String(length=500), nullable=True),
    sa.Column('phone_hash', sa.String(length=64), nullable=True),
    sa.Column('phone_encrypted', sa.String(length=500), nullable=True),
    sa.Column('hashed_password', sa.String(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('is_botanist', sa.Boolean(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email_hash'), 'users', ['email_hash'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_phone_hash'), 'users', ['phone_hash'], unique=False)
    op.create_index(op.f('ix_users_username_hash'), 'users', ['username_hash'], unique=True)
    op.create_table('plants',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=True),
    sa.Column('location', sa.String(), nullable=True),
    sa.Column('care_instructions', sa.String(), nullable=True),
    sa.Column('photo_url', sa.String(), nullable=True),
    sa.Column('owner_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('in_care_id', sa.Integer(), nullable=True),
    sa.Column('plant_sitting', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['in_care_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['plant_sitting'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_plants_id'), 'plants', ['id'], unique=False)
    op.create_index(op.f('ix_plants_name'), 'plants', ['name'], unique=False)
    op.create_table('commentary',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('plant_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('comment', sa.String(), nullable=False),
    sa.Column('time_stamp', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['plant_id'], ['plants.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_commentary_id'), 'commentary', ['id'], unique=False)



def downgrade() -> None:

    op.drop_index(op.f('ix_commentary_id'), table_name='commentary')
    op.drop_table('commentary')
    op.drop_index(op.f('ix_plants_name'), table_name='plants')
    op.drop_index(op.f('ix_plants_id'), table_name='plants')
    op.drop_table('plants')
    op.drop_index(op.f('ix_users_username_hash'), table_name='users')
    op.drop_index(op.f('ix_users_phone_hash'), table_name='users')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_index(op.f('ix_users_email_hash'), table_name='users')
    op.drop_table('users')
