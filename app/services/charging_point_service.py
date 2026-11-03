import uuid
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.charging_point import ChargingPoint
from app.schemas.charging_point import ChargingPointCreate, ChargingPointUpdate


class ChargingPointService:
    """Service layer handling business logic for Charging Points (EVSEs)."""

    @staticmethod
    def get_by_station(
        db: Session,
        station_id: uuid.UUID,
        status: Optional[str] = None,
        connector_type: Optional[str] = None,
        min_power_kw: Optional[float] = None,
    ) -> List[ChargingPoint]:
        """Fetch all charging points belonging to a station with optional filters."""
        query = db.query(ChargingPoint).filter(ChargingPoint.station_id == station_id)
        if status:
            query = query.filter(ChargingPoint.status == status.upper().strip())
        if connector_type:
            query = query.filter(ChargingPoint.connector_type == connector_type.upper().strip())
        if min_power_kw:
            query = query.filter(ChargingPoint.power_kw >= min_power_kw)
        return query.all()

    @staticmethod
    def get_by_id(db: Session, point_id: uuid.UUID) -> Optional[ChargingPoint]:
        """Fetch a single charging point by UUID."""
        return db.query(ChargingPoint).filter(ChargingPoint.id == point_id).first()

    @staticmethod
    def create(
        db: Session,
        station_id: uuid.UUID,
        point_in: ChargingPointCreate,
    ) -> ChargingPoint:
        """Create and persist a new charging point attached to a station."""
        db_point = ChargingPoint(
            station_id=station_id,
            identifier=point_in.identifier.strip(),
            connector_type=point_in.connector_type.upper().strip(),
            power_kw=point_in.power_kw,
            status=point_in.status.upper().strip(),
            price_per_kwh=point_in.price_per_kwh,
        )
        db.add(db_point)
        db.commit()
        db.refresh(db_point)
        return db_point

    @staticmethod
    def update(
        db: Session,
        point: ChargingPoint,
        point_in: ChargingPointUpdate,
    ) -> ChargingPoint:
        """Update existing charging point dispenser attributes."""
        update_data = point_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if isinstance(value, str):
                value = value.strip()
            setattr(point, field, value)

        db.commit()
        db.refresh(point)
        return point

    @staticmethod
    def delete(db: Session, point: ChargingPoint) -> None:
        """Delete an individual charging point dispenser."""
        db.delete(point)
        db.commit()

