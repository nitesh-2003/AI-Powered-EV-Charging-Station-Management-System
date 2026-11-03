import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.config import settings


@pytest.mark.asyncio
async def test_user_registration_and_authentication_flow():
    """Comprehensive test of registration, duplicate handling, login, /me, and RBAC."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        customer_email = "driver.jane@example.com"
        customer_password = "SecurePassword123!"

        # 1. Register a new Customer
        reg_response = await ac.post(
            f"{settings.API_V1_STR}/auth/register",
            json={
                "email": customer_email,
                "password": customer_password,
                "full_name": "Jane Driver",
                "role": "CUSTOMER",
            },
        )
        # Handle if already registered from a previous run or new
        assert reg_response.status_code in [201, 400]

        # 2. Verify duplicate registration fails with 400
        dup_response = await ac.post(
            f"{settings.API_V1_STR}/auth/register",
            json={
                "email": customer_email,
                "password": customer_password,
                "full_name": "Jane Driver Duplicate",
                "role": "CUSTOMER",
            },
        )
        assert dup_response.status_code == 400

        # 3. Verify login with wrong password fails with 401
        bad_login = await ac.post(
            f"{settings.API_V1_STR}/auth/login",
            json={"email": customer_email, "password": "WrongPassword!"},
        )
        assert bad_login.status_code == 401

        # 4. Verify login with correct password returns JWT
        login_response = await ac.post(
            f"{settings.API_V1_STR}/auth/login",
            json={"email": customer_email, "password": customer_password},
        )
        assert login_response.status_code == 200
        token_data = login_response.json()
        assert "access_token" in token_data
        customer_token = token_data["access_token"]

        # 5. Verify /me endpoint returns user profile
        headers = {"Authorization": f"Bearer {customer_token}"}
        me_response = await ac.get(f"{settings.API_V1_STR}/auth/me", headers=headers)
        assert me_response.status_code == 200
        user_info = me_response.json()
        assert user_info["email"] == customer_email
        assert user_info["role"] == "CUSTOMER"

        # 6. Verify Customer is BLOCKED from admin endpoint (HTTP 403 Forbidden)
        forbidden_resp = await ac.get(
            f"{settings.API_V1_STR}/auth/admin-test", headers=headers
        )
        assert forbidden_resp.status_code == 403

        # 7. Register an Administrator
        admin_email = "admin.operator@example.com"
        admin_password = "AdminMasterKey123!"
        await ac.post(
            f"{settings.API_V1_STR}/auth/register",
            json={
                "email": admin_email,
                "password": admin_password,
                "full_name": "Network Admin",
                "role": "ADMIN",
            },
        )

        # 8. Login as Administrator
        admin_login = await ac.post(
            f"{settings.API_V1_STR}/auth/login",
            json={"email": admin_email, "password": admin_password},
        )
        admin_token = admin_login.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # 9. Verify Admin has access to /admin-test (HTTP 200 OK)
        admin_resp = await ac.get(
            f"{settings.API_V1_STR}/auth/admin-test", headers=admin_headers
        )
        assert admin_resp.status_code == 200
        assert "privileged administrative access" in admin_resp.json()["message"]
