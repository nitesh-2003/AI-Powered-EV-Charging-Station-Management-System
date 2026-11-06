"""
Seed script to populate a fresh database with demo stations, dispensers,
users, bookings, sessions, and payments for demonstration and testing.

Usage:
    python -m scripts.seed_demo_data
"""
import uuid
from decimal import Decimal
from datetime import datetime, timedelta, timezone

from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.user import User
from app.models.station import ChargingStation
from app.models.charging_point import ChargingPoint
from app.models.booking import Booking
from app.models.charging_session import ChargingSession
from app.models.payment import Payment


def seed():
    db = SessionLocal()
    try:
        print("🌱 Seeding VoltFlow demonstration data...")

        # 1. Users
        admin = db.query(User).filter_by(email="admin@voltflow.io").first()
        if not admin:
            admin = User(
                email="admin@voltflow.io",
                hashed_password=get_password_hash("AdminPassword123!"),
                full_name="Network Operations Admin",
                role="ADMIN",
                is_active=True,
            )
            db.add(admin)
            print("  ✓ Created Admin: admin@voltflow.io (pwd: AdminPassword123!)")

        driver = db.query(User).filter_by(email="driver@voltflow.io").first()
        if not driver:
            driver = User(
                email="driver@voltflow.io",
                hashed_password=get_password_hash("DriverPassword123!"),
                full_name="Alex Mercer",
                role="CUSTOMER",
                is_active=True,
            )
            db.add(driver)
            print("  ✓ Created Customer: driver@voltflow.io (pwd: DriverPassword123!)")

        db.commit()
        db.refresh(admin)
        db.refresh(driver)

        # 2. Charging Stations
        stations_data = [
            {
                "name": "Downtown Fast Charging Hub",
                "address": "120 Financial District Blvd, Metro Center",
                "latitude": 12.9716,
                "longitude": 77.5946,
                "status": "ACTIVE",
                "points": [
                    {"identifier": "HUB-1A", "connector_type": "CCS2", "power_kw": 150.0, "status": "AVAILABLE", "price_per_kwh": Decimal("24.00")},
                    {"identifier": "HUB-1B", "connector_type": "CCS2", "power_kw": 120.0, "status": "OCCUPIED", "price_per_kwh": Decimal("22.00")},
                    {"identifier": "HUB-2A", "connector_type": "TYPE2", "power_kw": 22.0, "status": "AVAILABLE", "price_per_kwh": Decimal("14.00")},
                ],
            },
            {
                "name": "Northside Expressway Plaza",
                "address": "Mile Marker 14, Highway 80 Exit 4",
                "latitude": 13.0827,
                "longitude": 80.2707,
                "status": "ACTIVE",
                "points": [
                    {"identifier": "EXP-1", "connector_type": "CCS2", "power_kw": 180.0, "status": "AVAILABLE", "price_per_kwh": Decimal("26.00")},
                    {"identifier": "EXP-2", "connector_type": "CCS2", "power_kw": 150.0, "status": "AVAILABLE", "price_per_kwh": Decimal("24.00")},
                    {"identifier": "EXP-3", "connector_type": "CHADEMO", "power_kw": 50.0, "status": "AVAILABLE", "price_per_kwh": Decimal("18.00")},
                ],
            },
            {
                "name": "Westgate Tech Park Plaza",
                "address": "400 Innovation Way, Cyber City",
                "latitude": 17.3850,
                "longitude": 78.4867,
                "status": "ACTIVE",
                "points": [
                    {"identifier": "TECH-01", "connector_type": "CCS2", "power_kw": 120.0, "status": "AVAILABLE", "price_per_kwh": Decimal("20.00")},
                    {"identifier": "TECH-02", "connector_type": "TYPE2", "power_kw": 43.0, "status": "AVAILABLE", "price_per_kwh": Decimal("16.00")},
                    {"identifier": "TECH-03", "connector_type": "TYPE2", "power_kw": 22.0, "status": "AVAILABLE", "price_per_kwh": Decimal("14.00")},
                ],
            },
            {
                "name": "Airport Transit Supercharger",
                "address": "Terminal 2 Ground Transportation Center",
                "latitude": 19.0760,
                "longitude": 72.8777,
                "status": "ACTIVE",
                "points": [
                    {"identifier": "AIR-DC1", "connector_type": "CCS2", "power_kw": 250.0, "status": "AVAILABLE", "price_per_kwh": Decimal("28.00")},
                    {"identifier": "AIR-DC2", "connector_type": "CCS2", "power_kw": 150.0, "status": "AVAILABLE", "price_per_kwh": Decimal("24.00")},
                    {"identifier": "AIR-AC1", "connector_type": "TYPE2", "power_kw": 22.0, "status": "AVAILABLE", "price_per_kwh": Decimal("15.00")},
                ],
            },
        ]

        created_points = []
        for s_info in stations_data:
            existing = db.query(ChargingStation).filter_by(name=s_info["name"]).first()
            if not existing:
                st = ChargingStation(
                    name=s_info["name"],
                    address=s_info["address"],
                    latitude=s_info["latitude"],
                    longitude=s_info["longitude"],
                    status=s_info["status"],
                )
                db.add(st)
                db.commit()
                db.refresh(st)
                print(f"  ✓ Created Station: {st.name}")

                for p_info in s_info["points"]:
                    cp = ChargingPoint(
                        station_id=st.id,
                        identifier=p_info["identifier"],
                        connector_type=p_info["connector_type"],
                        power_kw=p_info["power_kw"],
                        status=p_info["status"],
                        price_per_kwh=p_info["price_per_kwh"],
                    )
                    db.add(cp)
                    created_points.append(cp)
                db.commit()
            else:
                created_points.extend(existing.charging_points)

        # 3. Sample Bookings & Sessions for Alex Mercer
        now = datetime.now(timezone.utc)
        if created_points:
            target_cp = created_points[0]
            existing_booking = db.query(Booking).filter_by(user_id=driver.id).first()
            if not existing_booking:
                # Past completed booking & session
                b1 = Booking(
                    user_id=driver.id,
                    charging_point_id=target_cp.id,
                    start_time=now - timedelta(days=1, hours=2),
                    end_time=now - timedelta(days=1, hours=1),
                    status="COMPLETED",
                )
                db.add(b1)
                db.commit()
                db.refresh(b1)

                energy_delivered = Decimal("32.40")
                tariff = target_cp.price_per_kwh
                cost = (energy_delivered * tariff).quantize(Decimal("0.01"))

                sess1 = ChargingSession(
                    booking_id=b1.id,
                    user_id=driver.id,
                    charging_point_id=target_cp.id,
                    start_time=now - timedelta(days=1, hours=2),
                    end_time=now - timedelta(days=1, hours=1, minutes=12),
                    initial_meter_kwh=Decimal("1240.00"),
                    final_meter_kwh=Decimal("1272.40"),
                    total_energy_kwh=energy_delivered,
                    total_cost=cost,
                    status="COMPLETED",
                )
                db.add(sess1)
                db.commit()
                db.refresh(sess1)

                pay1 = Payment(
                    session_id=sess1.id,
                    user_id=driver.id,
                    amount=cost,
                    status="COMPLETED",
                    transaction_ref=f"SIM-PAY-{uuid.uuid4().hex[:12].upper()}",
                )
                db.add(pay1)

                # Future upcoming reservation
                b2 = Booking(
                    user_id=driver.id,
                    charging_point_id=created_points[1].id if len(created_points) > 1 else target_cp.id,
                    start_time=now + timedelta(hours=3),
                    end_time=now + timedelta(hours=4),
                    status="CONFIRMED",
                )
                db.add(b2)
                db.commit()
                print("  ✓ Created sample completed session, payment invoice, and upcoming booking")

        print("✨ Seeding completed successfully!")
    finally:
        db.close()


if __name__ == "__main__":
    seed()

