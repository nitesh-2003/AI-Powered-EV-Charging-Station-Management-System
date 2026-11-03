import uuid
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.station import ChargingStation
from app.schemas.station import StationCreate, StationUpdate


class StationService:
    """Service layer handling business logic for Charging Stations."""

    @staticmethod
    def get_all(
        db: Session,
        status: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[ChargingStation]:
        """Fetch all stations with optional status filtering and name search."""
        query = db.query(ChargingStation)
        if status:
            query = query.filter(ChargingStation.status == status.upper().strip())
        if search:
            query = query.filter(ChargingStation.name.ilike(f"%{search.strip()}%"))
        return query.offset(skip).limit(limit).all()

    @staticmethod
    def get_by_id(db: Session, station_id: uuid.UUID) -> Optional[ChargingStation]:
        """Fetch a single station by UUID."""
        return db.query(ChargingStation).filter(ChargingStation.id == station_id).first()

    @staticmethod
    def create(db: Session, station_in: StationCreate) -> ChargingStation:
        """Create and persist a new charging station."""
        db_station = ChargingStation(
            name=station_in.name.strip(),
            address=station_in.address.strip(),
            latitude=station_in.latitude,
            longitude=station_in.longitude,
            status=station_in.status.upper().strip(),
        )
        db.add(db_station)
        db.commit()
        db.refresh(db_station)
        return db_station

    @staticmethod
    def update(
        db: Session,
        station: ChargingStation,
        station_in: StationUpdate,
    ) -> ChargingStation:
        """Update existing station fields."""
        update_data = station_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if isinstance(value, str):
                value = value.strip()
            setattr(station, field, value)

        db.commit()
        db.refresh(station)
        return station

    @staticmethod
    def delete(db: Session, station: ChargingStation) -> None:
        """Delete a station (cascades to all child charging points)."""
        db.delete(station)
        db.commit()

