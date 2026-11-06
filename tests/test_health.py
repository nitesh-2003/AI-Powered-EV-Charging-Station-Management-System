import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.config import settings


@pytest.mark.asyncio
async def test_root_endpoint():
    """Verify that root serves the customer web portal HTML."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/")
        assert response.status_code == 200
        assert "<!DOCTYPE html>" in response.text
        assert "VoltFlow" in response.text


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


@pytest.mark.asyncio
async def test_analytics_dashboard_endpoint():
    """Verify that admin can fetch aggregated operational analytics."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        admin_login = await ac.post(
            f"{settings.API_V1_STR}/auth/login",
            json={"email": "admin.operator@example.com", "password": "AdminMasterKey123!"},
        )
        admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}

        response = await ac.get(
            f"{settings.API_V1_STR}/analytics/dashboard",
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_users" in data
        assert "total_stations" in data
        assert "total_points" in data
        assert "revenue_trend" in data
        assert "station_breakdown" in data
