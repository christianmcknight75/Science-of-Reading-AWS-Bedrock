import os

from alembic import context
from sqlalchemy import create_engine

url = os.environ.get("DATABASE_URL", "postgresql://sor:local-dev-only@localhost:5433/sor").replace(
    "postgresql://", "postgresql+psycopg://", 1
)


def run_migrations_online() -> None:
    engine = create_engine(url)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=None)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
