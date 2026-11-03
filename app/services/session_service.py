import uuid
from decimal import Decimal
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.charging_session import ChargingSession
from app.models.charging_point import ChargingPoint
from app.models.booking import Booking
from app.models.payment import Payment
from app.models.user import User
from app.schemas.charging_session import SessionStart, SessionStop


class SessionService:
    """
    Service layer handling EV charging session state transitions,
    meter telemetry simulation, energy calculations, and billing generation.
    """

    @staticmethod
    def start_session(
        db: Session,
        user: User,
        session_in: SessionStart,
    ) -> ChargingSession:
        """
        Initiates a charging session.
        Validates hardware state, locks dispenser to 'OCCUPIED',
        and records initial energy meter reading.
        """
        # 1. Verify dispenser hardware state
        point = (
            db.query(ChargingPoint)
            .filter(ChargingPoint.id == session_in.charging_point_id)
            .first()
        )
        if not point:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Charging point dispenser not found",
            )

        if point.status == "OCCUPIED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Charging point dispenser is already occupied by an active session.",
            )

        if point.status == "FAULTED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Charging point dispenser is currently faulted for maintenance.",
            )

        # 2. Validate optional booking reservation
        if session_in.booking_id:
            booking = (
                db.query(Booking)
                .filter(Booking.id == session_in.booking_id)
                .first()
            )
            if not booking:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Referenced booking reservation not found",
                )
            if user.role != "ADMIN" and booking.user_id != user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Referenced booking belongs to another user account.",
                )
            if booking.status != "CONFIRMED":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Referenced booking has status '{booking.status}', expected 'CONFIRMED'.",
                )
            # Mark reservation as completed now that session has commenced
            booking.status = "COMPLETED"

        # 3. Record or simulate initial meter reading
        now = datetime.now(timezone.utc)
        initial_meter = (
            session_in.initial_meter_kwh
            if session_in.initial_meter_kwh is not None
            else Decimal("1000.00")
        )

        # 4. Create Charging Session
        session = ChargingSession(
            user_id=user.id,
            charging_point_id=point.id,
            booking_id=session_in.booking_id,
            start_time=now,
            initial_meter_kwh=initial_meter,
            status="IN_PROGRESS",
        )
        db.add(session)

        # 5. Toggle dispenser status to OCCUPIED
        point.status = "OCCUPIED"

        db.commit()
        db.refresh(session)
        return session

    @staticmethod
    def stop_session(
        db: Session,
        session_id: uuid.UUID,
        user: User,
        stop_in: SessionStop,
    ) -> ChargingSession:
        """
        Stops an active charging session.
        Calculates energy delivered (final - initial meter),
        multiplies by tariff (kWh * price), toggles dispenser back to AVAILABLE,
        and generates an itemized payment record.
        """
        session = (
            db.query(ChargingSession)
            .filter(ChargingSession.id == session_id)
            .first()
        )
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Charging session not found",
            )

        if user.role != "ADMIN" and session.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to stop this charging session.",
            )

        if session.status != "IN_PROGRESS":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot stop a session with status '{session.status}'.",
            )

        point = (
            db.query(ChargingPoint)
            .filter(ChargingPoint.id == session.charging_point_id)
            .first()
        )

        now = datetime.now(timezone.utc)

        # 1. Determine final meter reading
        if stop_in.final_meter_kwh is not None:
            if stop_in.final_meter_kwh < session.initial_meter_kwh:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Final meter reading cannot be less than initial meter reading.",
                )
            final_meter = stop_in.final_meter_kwh
        else:
            # Default simulation: 28.5 kWh delivered
            final_meter = session.initial_meter_kwh + Decimal("28.50")

        # 2. Calculate Energy & Cost
        # Energy = Final Meter - Initial Meter
        # Cost = Energy * Price per kWh
        total_energy = final_meter - session.initial_meter_kwh
        price_rate = point.price_per_kwh if point else Decimal("15.00")
        total_cost = (total_energy * price_rate).quantize(Decimal("0.01"))

        # 3. Update session state
        session.end_time = now
        session.final_meter_kwh = final_meter
        session.total_energy_kwh = total_energy
        session.total_cost = total_cost
        session.status = "COMPLETED"

        # 4. Toggle dispenser status back to AVAILABLE
        if point:
            point.status = "AVAILABLE"

        # 5. Generate simulated payment record
        transaction_ref = f"SIM-PAY-{uuid.uuid4().hex[:12].upper()}"
        payment = Payment(
            session_id=session.id,
            user_id=session.user_id,
            amount=total_cost,
            status="COMPLETED",
            transaction_ref=transaction_ref,
        )
        db.add(payment)

        db.commit()
        db.refresh(session)
        return session

    @staticmethod
    def get_by_id(db: Session, session_id: uuid.UUID) -> Optional[ChargingSession]:
        """Fetch session by ID."""
        return (
            db.query(ChargingSession)
            .filter(ChargingSession.id == session_id)
            .first()
        )

    @staticmethod
    def get_user_sessions(db: Session, user_id: uuid.UUID) -> List[ChargingSession]:
        """Fetch charging session history for a specific customer."""
        return (
            db.query(ChargingSession)
            .filter(ChargingSession.user_id == user_id)
            .order_by(ChargingSession.start_time.desc())
            .all()
        )

    @staticmethod
    def get_all(
        db: Session,
        status: Optional[str] = None,
    ) -> List[ChargingSession]:
        """Admin query: fetch all network charging sessions."""
        query = db.query(ChargingSession)
        if status:
            query = query.filter(ChargingSession.status == status.upper().strip())
        return query.order_by(ChargingSession.start_time.desc()).all()
