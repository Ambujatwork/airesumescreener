from logging.config import fileConfig
import os
import sys
import socket
from dotenv import load_dotenv

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import your models
from src.database import Base
from src.models.user import User  # Make sure to import all your models

# Load environment variables
load_dotenv()

# Get the original DATABASE_URL 
original_db_url = os.getenv("DATABASE_URL")

# Function to check if a host is available
def is_host_available(host, port=5432, timeout=1):
    try:
        socket.create_connection((host, port), timeout=timeout)
        return True
    except (socket.timeout, socket.error):
        return False

# Parse the DATABASE_URL to get components
if original_db_url and "db" in original_db_url:
    # If "db" is in the URL but not available, replace with localhost
    if not is_host_available("db"):
        database_url = original_db_url.replace("@db:", "@localhost:")
    else:
        database_url = original_db_url
else:
    # Fallback if DATABASE_URL is not set
    db_user = os.getenv("POSTGRES_USER", "admin")
    db_password = os.getenv("POSTGRES_PASSWORD", "secret")
    db_name = os.getenv("POSTGRES_DB", "resume_screener")
    
    # Try db first, fallback to localhost if not available
    if is_host_available("db"):
        db_host = "db"
    else:
        db_host = "localhost"
    
    database_url = f"postgresql://{db_user}:{db_password}@{db_host}:5432/{db_name}"

# Alembic Config object
config = context.config

# Override sqlalchemy.url with dynamic URL
config.set_main_option("sqlalchemy.url", database_url)

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()