import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import require_admin
from app.models.user import User
from app.schemas.charging_point import ChargingPointUpdate, ChargingPointResponse
from app.services.charging_point_service import ChargingPointService

router = APIRouter()


@router.get(
    "/{point_id}",
    response_model=ChargingPointResponse,
    summary="Get single charging point details",
)
def get_charging_point(
    point_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """Retrieve details of an individual charging dispenser."""
    point = ChargingPointService.get_by_id(db, point_id=point_id)
    if not point:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Charging point not found",
        )
    return point


@router.put(
    "/{point_id}",
    response_model=ChargingPointResponse,
    summary="Update charging point status or tariff (Admin Only)",
)
def update_charging_point(
    point_id: uuid.UUID,
    point_in: ChargingPointUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    """Update dispenser operating state, tariff, or power output."""
    point = ChargingPointService.get_by_id(db, point_id=point_id)
    if not point:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Charging point not found",
        )
    return ChargingPointService.update(db, point=point, point_in=point_in)


@router.delete(
    "/{point_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an individual charging point (Admin Only)",
)
def delete_charging_point(
    point_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    """Decommission and remove an individual charging dispenser."""
    point = ChargingPointService.get_by_id(db, point_id=point_id)
    if not point:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Charging point not found",
        )
    ChargingPointService.delete(db, point=point)
    return None

