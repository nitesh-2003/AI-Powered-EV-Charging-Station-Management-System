import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import TimestampedModel

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.charging_point import ChargingPoint
    from app.models.charging_session import ChargingSession


class Booking(TimestampedModel):
    """
    Time-slot reservation for a specific charging dispenser (EVSE).
    """
    __tablename__ = "bookings"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Driver who made the reservation",
    )

    charging_point_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("charging_points.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Reserved charging point dispenser",
    )

    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        doc="Reservation window start time",
    )

    end_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        doc="Reservation window end time",
    )

    status: Mapped[str] = mapped_column(
        String(20),
        default="CONFIRMED",
        nullable=False,
        index=True,
        doc="Status: 'CONFIRMED', 'CANCELLED', 'COMPLETED'",
    )

    # Relationships
    user: Mapped["User"] = relationship("User", lazy="selectin")
    charging_point: Mapped["ChargingPoint"] = relationship("ChargingPoint", lazy="selectin")
    session: Mapped[Optional["ChargingSession"]] = relationship(
        "ChargingSession",
        back_populates="booking",
        uselist=False,
    )

    def __repr__(self) -> str:
        return f"<Booking id={self.id} point_id={self.charging_point_id} status={self.status}>"
