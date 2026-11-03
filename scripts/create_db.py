import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from app.core.config import settings


def init_db():
    """Connect to default 'postgres' database and create 'ev_charging_db' if it doesn't exist."""
    conn = psycopg2.connect(
        dbname="postgres",
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        host=settings.POSTGRES_SERVER,
        port=settings.POSTGRES_PORT,
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT 1 FROM pg_database WHERE datname = %s;", (settings.POSTGRES_DB,)
    )
    exists = cursor.fetchone()
    if not exists:
        cursor.execute(f'CREATE DATABASE "{settings.POSTGRES_DB}";')
        print(f"Database '{settings.POSTGRES_DB}' created successfully!")
    else:
        print(f"Database '{settings.POSTGRES_DB}' already exists.")

    cursor.close()
    conn.close()


if __name__ == "__main__":
    init_db()
