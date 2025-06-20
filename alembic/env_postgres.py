# alembic/env.py (updated for PostgreSQL)
from logging.config import fileConfig
import os
import sys
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context

# This is the path to your project root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

# Import the MetaData object from your models
from app.models import Base
from app.config import get_database_url

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set the MetaData object for autogenerate support
target_metadata = Base.metadata

# Set the database URL from our configuration
config.set_main_option('sqlalchemy.url', get_database_url())

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Create engine with PostgreSQL-specific settings
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        # PostgreSQL specific options
        connect_args={
            "options": "-c timezone=utc"
        }
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            # PostgreSQL specific options for migrations
            render_as_batch=False,  # PostgreSQL supports ALTER TABLE directly
        )

        with context.begin_transaction():
            context.run_migrations()

# Run migrations based on context
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()