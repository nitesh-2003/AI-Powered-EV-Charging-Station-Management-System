import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import require_admin
from app.models.user import User
from app.schemas.station import StationCreate, StationUpdate, StationResponse
from app.schemas.charging_point import ChargingPointCreate, ChargingPointResponse
from app.services.station_service import StationService
from app.services.charging_point_service import ChargingPointService

router = APIRouter()


@router.get(
    "",
    response_model=List[StationResponse],
    summary="List all charging stations",
    description="Public endpoint to discover charging stations with optional status filtering and name search.",
)
@router.get(
    "/",
    response_model=List[StationResponse],
    include_in_schema=False,
)
def list_stations(
    status: Optional[str] = Query(None, description="Filter by status ('ACTIVE', 'INACTIVE')"),
    search: Optional[str] = Query(None, description="Search keyword for station name"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Retrieve all charging station plazas."""
    return StationService.get_all(db, status=status, search=search, skip=skip, limit=limit)


@router.get(
    "/{station_id}",
    response_model=StationResponse,
    summary="Get single charging station details",
)
def get_station(
    station_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """Retrieve station details and its operational charging points."""
    station = StationService.get_by_id(db, station_id=station_id)
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Charging station not found",
        )
    return station


@router.post(
    "",
    response_model=StationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new charging station plaza (Admin Only)",
)
@router.post(
    "/",
    response_model=StationResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
def create_station(
    station_in: StationCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    """Registers a new charging station. Restricted to Administrators."""
    return StationService.create(db, station_in=station_in)


@router.put(
    "/{station_id}",
    response_model=StationResponse,
    summary="Update charging station details (Admin Only)",
)
def update_station(
    station_id: uuid.UUID,
    station_in: StationUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    """Updates station parameters. Restricted to Administrators."""
    station = StationService.get_by_id(db, station_id=station_id)
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Charging station not found",
        )
    return StationService.update(db, station=station, station_in=station_in)


@router.delete(
    "/{station_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a charging station (Admin Only)",
)
def delete_station(
    station_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    """Deletes a charging station and all child dispensers. Restricted to Administrators."""
    station = StationService.get_by_id(db, station_id=station_id)
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Charging station not found",
        )
    StationService.delete(db, station=station)
    return None


# --- Nested Charging Point Endpoints ---

@router.post(
    "/{station_id}/points",
    response_model=ChargingPointResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a charging point to a station (Admin Only)",
)
def add_charging_point_to_station(
    station_id: uuid.UUID,
    point_in: ChargingPointCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    """Adds a new charging dispenser to the specified station."""
    station = StationService.get_by_id(db, station_id=station_id)
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parent charging station not found",
        )
    return ChargingPointService.create(db, station_id=station_id, point_in=point_in)


@router.get(
    "/{station_id}/points",
    response_model=List[ChargingPointResponse],
    summary="List charging points for a station with filters",
)
def list_station_charging_points(
    station_id: uuid.UUID,
    status: Optional[str] = Query(None, description="Filter: 'AVAILABLE', 'OCCUPIED'"),
    connector_type: Optional[str] = Query(None, description="Filter: 'CCS2', 'TYPE2', 'CHADEMO'"),
    min_power_kw: Optional[float] = Query(None, description="Minimum power in kW"),
    db: Session = Depends(get_db),
):
    """Lists dispensers for a station with optional connector and power filters."""
    station = StationService.get_by_id(db, station_id=station_id)
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Charging station not found",
        )
    return ChargingPointService.get_by_station(
        db,
        station_id=station_id,
        status=status,
        connector_type=connector_type,
        min_power_kw=min_power_kw,
    )
