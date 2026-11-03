import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.config import settings


@pytest.mark.asyncio
async def test_root_endpoint():
    """Verify that the root endpoint returns HTTP 200 and points to API docs."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "online"
        assert data["documentation"] == "/docs"
        assert f"{settings.API_V1_STR}/health" in data["health_check"]


@pytest.mark.asyncio
async def test_health_check_endpoint():
    """Verify that the health check endpoint returns 200 and correct service metadata."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(f"{settings.API_V1_STR}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == settings.PROJECT_NAME
        assert data["version"] == settings.VERSION
        assert "environment" in data
