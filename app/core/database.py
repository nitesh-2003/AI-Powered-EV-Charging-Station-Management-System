import logging
import socket
from typing import Generator
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.compiler import compiles
from app.core.config import settings

logger = logging.getLogger(__name__)

# Declarative base class for all ORM models
Base = declarative_base()

# Teach SQLAlchemy to compile PostgreSQL UUID to CHAR(36) when using SQLite
@compiles(PG_UUID, "sqlite")
def compile_uuid_sqlite(type_, compiler, **kw):
    return "CHAR(36)"


def _is_postgres_reachable(host: str, port: int, timeout: float = 1.0) -> bool:
    """Test TCP socket reachability for PostgreSQL before attempting engine connection."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        result = s.connect_ex((host, port))
        s.close()
        return result == 0
    except Exception:
        return False


# Determine database connection target
db_url = settings.DATABASE_URL
use_sqlite_fallback = False

if db_url.startswith("postgresql") and settings.DEBUG:
    if not _is_postgres_reachable(settings.POSTGRES_SERVER, settings.POSTGRES_PORT):
        logger.warning(
            "⚠️ PostgreSQL is unreachable at %s:%s. Activating local SQLite development database (ev_charging_dev.db)",
            settings.POSTGRES_SERVER,
            settings.POSTGRES_PORT,
        )
        db_url = "sqlite:///./ev_charging_dev.db"
        use_sqlite_fallback = True

if db_url.startswith("sqlite"):
    engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False},
        echo=False,
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
else:
    engine = create_engine(
        db_url,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        echo=settings.DEBUG,
    )

# Session factory for creating database sessions
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a database session per request.
    Ensures the session is always closed after the request is processed,
    returning the connection to the pool.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

