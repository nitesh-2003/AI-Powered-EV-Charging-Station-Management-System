import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.config import settings


@pytest.mark.asyncio
async def test_stations_and_charging_points_lifecycle():
    """Verify full CRUD, RBAC restrictions, filtering, and cascading delete."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Setup Admin and Customer users
        admin_login = await ac.post(
            f"{settings.API_V1_STR}/auth/login",
            json={"email": "admin.operator@example.com", "password": "AdminMasterKey123!"},
        )
        if admin_login.status_code != 200:
            await ac.post(
                f"{settings.API_V1_STR}/auth/register",
                json={
                    "email": "admin.operator@example.com",
                    "password": "AdminMasterKey123!",
                    "full_name": "Station Admin",
                    "role": "ADMIN",
                },
            )
            admin_login = await ac.post(
                f"{settings.API_V1_STR}/auth/login",
                json={"email": "admin.operator@example.com", "password": "AdminMasterKey123!"},
            )
        admin_token = admin_login.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # Customer token
        cust_login = await ac.post(
            f"{settings.API_V1_STR}/auth/login",
            json={"email": "driver.jane@example.com", "password": "SecurePassword123!"},
        )
        cust_token = cust_login.json()["access_token"]
        cust_headers = {"Authorization": f"Bearer {cust_token}"}

        # 2. Verify Public user can read stations without auth
        public_resp = await ac.get(f"{settings.API_V1_STR}/stations")
        assert public_resp.status_code == 200

        # 3. Verify Customer is FORBIDDEN from creating stations (403)
        station_payload = {
            "name": "Highway Supercharger Hub",
            "address": "Expressway Mile 42, Service Area",
            "latitude": 13.0827,
            "longitude": 80.2707,
            "status": "ACTIVE",
        }
        forbidden_create = await ac.post(
            f"{settings.API_V1_STR}/stations",
            json=station_payload,
            headers=cust_headers,
        )
        assert forbidden_create.status_code == 403

        # 4. Verify Admin can create a station (201)
        create_resp = await ac.post(
            f"{settings.API_V1_STR}/stations",
            json=station_payload,
            headers=admin_headers,
        )
        assert create_resp.status_code == 201
        station_data = create_resp.json()
        station_id = station_data["id"]
        assert station_data["name"] == station_payload["name"]

        # 5. Verify Admin can add charging points to the station (201)
        cp_payload = {
            "identifier": "DISPENSER-1A",
            "connector_type": "CCS2",
            "power_kw": 120.0,
            "status": "AVAILABLE",
            "price_per_kwh": 22.50,
        }
        add_cp_resp = await ac.post(
            f"{settings.API_V1_STR}/stations/{station_id}/points",
            json=cp_payload,
            headers=admin_headers,
        )
        assert add_cp_resp.status_code == 201
        cp_data = add_cp_resp.json()
        point_id = cp_data["id"]
        assert cp_data["connector_type"] == "CCS2"
        assert cp_data["power_kw"] == 120.0

        # Add a second point (Type 2, 22kW)
        await ac.post(
            f"{settings.API_V1_STR}/stations/{station_id}/points",
            json={
                "identifier": "DISPENSER-2B",
                "connector_type": "TYPE2",
                "power_kw": 22.0,
                "status": "AVAILABLE",
                "price_per_kwh": 14.00,
            },
            headers=admin_headers,
        )

        # 6. Verify station details now contains 2 nested points
        station_detail = await ac.get(f"{settings.API_V1_STR}/stations/{station_id}")
        assert station_detail.status_code == 200
        points_list = station_detail.json()["charging_points"]
        assert len(points_list) == 2

        # 7. Verify filtering points by connector and min power
        filtered_resp = await ac.get(
            f"{settings.API_V1_STR}/stations/{station_id}/points?connector_type=CCS2&min_power_kw=50"
        )
        assert filtered_resp.status_code == 200
        filtered_points = filtered_resp.json()
        assert len(filtered_points) == 1
        assert filtered_points[0]["identifier"] == "DISPENSER-1A"

        # 8. Verify updating a point status and price
        update_cp_resp = await ac.put(
            f"{settings.API_V1_STR}/points/{point_id}",
            json={"status": "OCCUPIED", "price_per_kwh": 25.00},
            headers=admin_headers,
        )
        assert update_cp_resp.status_code == 200
        assert update_cp_resp.json()["status"] == "OCCUPIED"

        # 9. Verify deleting the station cascades and deletes the points
        del_resp = await ac.delete(
            f"{settings.API_V1_STR}/stations/{station_id}",
            headers=admin_headers,
        )
        assert del_resp.status_code == 204

        # Verify station and point are gone (404)
        assert (await ac.get(f"{settings.API_V1_STR}/stations/{station_id}")).status_code == 404
        assert (await ac.get(f"{settings.API_V1_STR}/points/{point_id}")).status_code == 404
