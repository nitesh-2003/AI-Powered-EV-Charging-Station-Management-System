"""
Pytest configuration and shared test fixtures.
Sets up an in-memory SQLite database with dialect adapters for PostgreSQL UUID,
enables foreign key cascades, and wires FastAPI dependency overrides.
"""
import uuid
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.compiler import compiles
from httpx import AsyncClient, ASGITransport

# 1. Teach SQLAlchemy compiler to render PostgreSQL UUIDs as CHAR(36) in SQLite
@compiles(PG_UUID, "sqlite")
def compile_uuid_sqlite(type_, compiler, **kw):
    return "CHAR(36)"

# 2. Create in-memory SQLite engine with connection pooling and FK enforcement
TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

@event.listens_for(test_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

# 3. Patch app.core.database singleton to point to test engine
import app.core.database as app_db
from app.models import Base
from app.main import app

TestSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
)

app_db.engine = test_engine
app_db.SessionLocal = TestSessionLocal

# Create all schema tables
Base.metadata.create_all(bind=test_engine)

# 4. Dependency override for FastAPI get_db
def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[app_db.get_db] = override_get_db


@pytest.fixture(scope="session")
def engine():
    """Provides the session-scoped SQLite test engine."""
    return test_engine


@pytest.fixture(scope="function")
def db_session():
    """Provides a transactional database session for unit tests."""
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client():
    """Provides an ASGITransport instance for HTTP client tests."""
    return ASGITransport(app=app)

