import uuid
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.booking import Booking
from app.models.charging_point import ChargingPoint
from app.models.user import User
from app.schemas.booking import BookingCreate


class BookingService:
    """
    Service layer implementing concurrency-controlled slot reservations
    with PostgreSQL row-level locking to prevent double bookings.
    """

    @staticmethod
    def create_booking(
        db: Session,
        user_id: uuid.UUID,
        booking_in: BookingCreate,
    ) -> Booking:
        """
        Creates a time-slot reservation.
        Uses SELECT ... FOR UPDATE to lock the target dispenser row,
        guaranteeing zero race conditions during concurrent booking requests.
        """
        # Ensure reservation is not in the past (allow small 1-minute grace for clock skew)
        now = datetime.now(timezone.utc)
        if booking_in.end_time <= now:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot reserve a time slot entirely in the past.",
            )

        # 1. ACQUIRE EXCLUSIVE ROW LOCK ON THE CHARGING POINT
        # Any concurrent booking for this same point will wait until this transaction completes.
        point = (
            db.query(ChargingPoint)
            .filter(ChargingPoint.id == booking_in.charging_point_id)
            .with_for_update()
            .first()
        )

        if not point:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Charging point dispenser not found",
            )

        if point.status == "FAULTED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Charging point is currently marked as FAULTED for maintenance.",
            )

        # 2. OVERLAP DETECTION QUERY WITHIN THE LOCK BOUNDARY
        # Interval intersection condition: start_time < requested_end AND end_time > requested_start
        overlapping_booking = (
            db.query(Booking)
            .filter(
                Booking.charging_point_id == booking_in.charging_point_id,
                Booking.status == "CONFIRMED",
                and_(
                    Booking.start_time < booking_in.end_time,
                    Booking.end_time > booking_in.start_time,
                ),
            )
            .first()
        )

        if overlapping_booking:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Time slot conflict: Dispenser is already reserved from "
                    f"{overlapping_booking.start_time.isoformat()} to {overlapping_booking.end_time.isoformat()}."
                ),
            )

        # 3. PERSIST CONFIRMED BOOKING
        db_booking = Booking(
            user_id=user_id,
            charging_point_id=booking_in.charging_point_id,
            start_time=booking_in.start_time,
            end_time=booking_in.end_time,
            status="CONFIRMED",
        )
        db.add(db_booking)
        db.commit()
        db.refresh(db_booking)
        return db_booking

    @staticmethod
    def get_by_id(db: Session, booking_id: uuid.UUID) -> Optional[Booking]:
        """Fetch booking by ID."""
        return db.query(Booking).filter(Booking.id == booking_id).first()

    @staticmethod
    def get_user_bookings(db: Session, user_id: uuid.UUID) -> List[Booking]:
        """Fetch all reservations for a given customer."""
        return (
            db.query(Booking)
            .filter(Booking.user_id == user_id)
            .order_by(Booking.start_time.desc())
            .all()
        )

    @staticmethod
    def get_all(db: Session, status: Optional[str] = None) -> List[Booking]:
        """Admin query: fetch all bookings across the network with optional status filter."""
        query = db.query(Booking)
        if status:
            query = query.filter(Booking.status == status.upper().strip())
        return query.order_by(Booking.start_time.desc()).all()

    @staticmethod
    def cancel_booking(
        db: Session,
        booking_id: uuid.UUID,
        user: User,
    ) -> Booking:
        """Cancel a reservation. Non-admins can only cancel their own bookings."""
        booking = BookingService.get_by_id(db, booking_id=booking_id)
        if not booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Booking reservation not found",
            )

        if user.role != "ADMIN" and booking.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to cancel this booking.",
            )

        if booking.status != "CONFIRMED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel a booking with status '{booking.status}'.",
            )

        booking.status = "CANCELLED"
        db.commit()
        db.refresh(booking)
        return booking

