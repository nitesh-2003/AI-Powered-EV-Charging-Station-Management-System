import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.config import settings


@pytest.mark.asyncio
async def test_bookings_concurrency_overlap_and_sessions_billing_flow():
    """
    Comprehensive test covering:
    - Time-slot reservation
    - Strict rejection of overlapping bookings (HTTP 409 Conflict)
    - Successful non-overlapping bookings
    - Session start with initial meter and hardware lock
    - Rejection of concurrent session on occupied charger
    - Session stop with final meter, energy consumed calculation, and invoice generation
    - Booking cancellation
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Login Admin
        admin_login = await ac.post(
            f"{settings.API_V1_STR}/auth/login",
            json={"email": "admin.operator@example.com", "password": "AdminMasterKey123!"},
        )
        admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}

        # 2. Login Driver A
        driver_a_login = await ac.post(
            f"{settings.API_V1_STR}/auth/login",
            json={"email": "driver.jane@example.com", "password": "SecurePassword123!"},
        )
        driver_a_headers = {"Authorization": f"Bearer {driver_a_login.json()['access_token']}"}

        # 3. Register and Login Driver B
        driver_b_email = "driver.bob@example.com"
        await ac.post(
            f"{settings.API_V1_STR}/auth/register",
            json={
                "email": driver_b_email,
                "password": "PasswordBob456!",
                "full_name": "Bob Driver",
                "role": "CUSTOMER",
            },
        )
        driver_b_login = await ac.post(
            f"{settings.API_V1_STR}/auth/login",
            json={"email": driver_b_email, "password": "PasswordBob456!"},
        )
        driver_b_headers = {"Authorization": f"Bearer {driver_b_login.json()['access_token']}"}

        # 4. Create a Test Station & Charging Point (Tariff: $20.00 / kWh)
        station_res = await ac.post(
            f"{settings.API_V1_STR}/stations",
            json={
                "name": "Midtown Fast Plaza",
                "address": "456 Tech Parkway",
                "latitude": 37.7749,
                "longitude": -122.4194,
                "status": "ACTIVE",
            },
            headers=admin_headers,
        )
        station_id = station_res.json()["id"]

        point_res = await ac.post(
            f"{settings.API_V1_STR}/stations/{station_id}/points",
            json={
                "identifier": "FAST-01",
                "connector_type": "CCS2",
                "power_kw": 150.0,
                "status": "AVAILABLE",
                "price_per_kwh": 20.00,
            },
            headers=admin_headers,
        )
        point_id = point_res.json()["id"]

        # 5. Driver A reserves slot: T + 2 hours to T + 3 hours
        now = datetime.now(timezone.utc)
        slot1_start = now + timedelta(hours=2)
        slot1_end = now + timedelta(hours=3)

        booking1_res = await ac.post(
            f"{settings.API_V1_STR}/bookings",
            json={
                "charging_point_id": point_id,
                "start_time": slot1_start.isoformat(),
                "end_time": slot1_end.isoformat(),
            },
            headers=driver_a_headers,
        )
        assert booking1_res.status_code == 201
        booking1_id = booking1_res.json()["id"]
        assert booking1_res.json()["status"] == "CONFIRMED"

        # 6. CONCURRENCY OVERLAP CHECK: Driver B tries to reserve an OVERLAPPING slot (T + 2h30m to T + 3h30m)
        slot_overlap_start = now + timedelta(hours=2, minutes=30)
        slot_overlap_end = now + timedelta(hours=3, minutes=30)

        conflict_res = await ac.post(
            f"{settings.API_V1_STR}/bookings",
            json={
                "charging_point_id": point_id,
                "start_time": slot_overlap_start.isoformat(),
                "end_time": slot_overlap_end.isoformat(),
            },
            headers=driver_b_headers,
        )
        # CRITICAL ASSERTION: Overlap must be rejected with HTTP 409 Conflict!
        assert conflict_res.status_code == 409
        assert "Time slot conflict" in conflict_res.json()["detail"]

        # 7. Driver B books NON-OVERLAPPING slot: T + 3 hours to T + 4 hours -> Success (201)
        slot2_start = now + timedelta(hours=3)
        slot2_end = now + timedelta(hours=4)

        booking2_res = await ac.post(
            f"{settings.API_V1_STR}/bookings",
            json={
                "charging_point_id": point_id,
                "start_time": slot2_start.isoformat(),
                "end_time": slot2_end.isoformat(),
            },
            headers=driver_b_headers,
        )
        assert booking2_res.status_code == 201

        # 8. Start Charging Session for Driver A
        # Initial Meter = 5000.00 kWh
        start_session_res = await ac.post(
            f"{settings.API_V1_STR}/sessions/start",
            json={
                "charging_point_id": point_id,
                "booking_id": booking1_id,
                "initial_meter_kwh": 5000.00,
            },
            headers=driver_a_headers,
        )
        assert start_session_res.status_code == 201
        session_data = start_session_res.json()
        session_id = session_data["id"]
        assert session_data["status"] == "IN_PROGRESS"
        assert float(session_data["initial_meter_kwh"]) == 5000.00

        # Verify dispenser status toggled to OCCUPIED
        dispenser_check = await ac.get(f"{settings.API_V1_STR}/points/{point_id}")
        assert dispenser_check.json()["status"] == "OCCUPIED"

        # Verify attempting to start another session on occupied charger fails (400)
        blocked_session = await ac.post(
            f"{settings.API_V1_STR}/sessions/start",
            json={"charging_point_id": point_id},
            headers=driver_b_headers,
        )
        assert blocked_session.status_code == 400

        # 9. Stop Charging Session
        # Final Meter = 5040.50 kWh
        # Energy Delivered = 5040.50 - 5000.00 = 40.50 kWh
        # Expected Cost = 40.50 kWh * 20.00 $/kWh = $810.00
        stop_session_res = await ac.post(
            f"{settings.API_V1_STR}/sessions/{session_id}/stop",
            json={"final_meter_kwh": 5040.50},
            headers=driver_a_headers,
        )
        assert stop_session_res.status_code == 200
        completed_session = stop_session_res.json()
        assert completed_session["status"] == "COMPLETED"
        assert float(completed_session["total_energy_kwh"]) == 40.50
        assert float(completed_session["total_cost"]) == 810.00

        # Verify simulated payment invoice was created
        assert completed_session["payment"] is not None
        assert float(completed_session["payment"]["amount"]) == 810.00
        assert completed_session["payment"]["status"] == "COMPLETED"
        assert "SIM-PAY-" in completed_session["payment"]["transaction_ref"]

        # Verify dispenser returned to AVAILABLE
        dispenser_after = await ac.get(f"{settings.API_V1_STR}/points/{point_id}")
        assert dispenser_after.json()["status"] == "AVAILABLE"

        # 10. Driver B cancels their future reservation
        cancel_res = await ac.post(
            f"{settings.API_V1_STR}/bookings/{booking2_res.json()['id']}/cancel",
            headers=driver_b_headers,
        )
        assert cancel_res.status_code == 200
        assert cancel_res.json()["status"] == "CANCELLED"

        # 11. Cleanup test station
        await ac.delete(f"{settings.API_V1_STR}/stations/{station_id}", headers=admin_headers)

