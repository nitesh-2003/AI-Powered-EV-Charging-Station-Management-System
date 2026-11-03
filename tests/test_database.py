import pytest
from sqlalchemy import text
from app.core.database import SessionLocal
from app.models.station import ChargingStation
from app.models.charging_point import ChargingPoint


def test_database_connection():
    """Verify that PostgreSQL connection succeeds and responds to queries."""
    db = SessionLocal()
    try:
        result = db.execute(text("SELECT 1")).scalar()
        assert result == 1
    finally:
        db.close()


def test_create_station_and_charging_point_relationship():
    """Verify ORM model creation and foreign key cascade relationship."""
    db = SessionLocal()
    try:
        # Create station
        station = ChargingStation(
            name="Test Metro Hub",
            address="100 Electric Avenue, Sector 5",
            latitude=12.9716,
            longitude=77.5946,
            status="ACTIVE",
        )
        db.add(station)
        db.commit()
        db.refresh(station)

        # Create charging point attached to station
        point = ChargingPoint(
            station_id=station.id,
            identifier="BAY-01",
            connector_type="CCS2",
            power_kw=60.0,
            status="AVAILABLE",
            price_per_kwh=18.50,
        )
        db.add(point)
        db.commit()
        db.refresh(point)

        # Query and verify relationship
        fetched_station = db.query(ChargingStation).filter_by(id=station.id).first()
        assert fetched_station is not None
        assert len(fetched_station.charging_points) == 1
        assert fetched_station.charging_points[0].identifier == "BAY-01"
        assert fetched_station.charging_points[0].connector_type == "CCS2"

        # Cleanup test records
        db.delete(fetched_station)
        db.commit()

        # Verify cascading delete
        orphaned_point = db.query(ChargingPoint).filter_by(id=point.id).first()
        assert orphaned_point is None
    finally:
        db.close()

