import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_active_user, require_admin
from app.models.user import User
from app.schemas.booking import BookingCreate, BookingResponse
from app.services.booking_service import BookingService

router = APIRouter()


@router.post(
    "",
    response_model=BookingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Reserve a charging time slot (Driver)",
)
@router.post(
    "/",
    response_model=BookingResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
def create_booking(
    booking_in: BookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Reserves a charging point dispenser for a specified time window.
    Guaranteed concurrency safe with database row locking.
    """
    return BookingService.create_booking(db, user_id=current_user.id, booking_in=booking_in)


@router.get(
    "/my",
    response_model=List[BookingResponse],
    summary="Get authenticated customer's booking history",
)
def get_my_bookings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Returns all reservations placed by the currently logged-in user."""
    return BookingService.get_user_bookings(db, user_id=current_user.id)


@router.get(
    "",
    response_model=List[BookingResponse],
    summary="List all network reservations (Admin Only)",
)
@router.get(
    "/",
    response_model=List[BookingResponse],
    include_in_schema=False,
)
def list_all_bookings(
    status: Optional[str] = Query(None, description="Filter: 'CONFIRMED', 'CANCELLED', 'COMPLETED'"),
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(100, ge=1, le=500, description="Pagination limit"),
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    """Admin-only view of all reservations across the charging network."""
    return BookingService.get_all(db, status=status, skip=skip, limit=limit)


@router.get(
    "/{booking_id}",
    response_model=BookingResponse,
    summary="Get single booking reservation details",
)
def get_booking_details(
    booking_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Retrieve details of a specific reservation."""
    booking = BookingService.get_by_id(db, booking_id=booking_id)
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking reservation not found",
        )
    if current_user.role != "ADMIN" and booking.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to reservation details",
        )
    return booking


@router.post(
    "/{booking_id}/cancel",
    response_model=BookingResponse,
    summary="Cancel a booking reservation",
)
def cancel_booking(
    booking_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Cancels a confirmed reservation."""
    return BookingService.cancel_booking(db, booking_id=booking_id, user=current_user)

