import uuid
from decimal import Decimal
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, DateTime, Numeric, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import TimestampedModel

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.charging_point import ChargingPoint
    from app.models.booking import Booking
    from app.models.payment import Payment


class ChargingSession(TimestampedModel):
    """
    Physical or simulated EV charging delivery session.
    """
    __tablename__ = "charging_sessions"

    booking_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bookings.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Optional reservation that initiated this session",
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Driver charging their vehicle",
    )

    charging_point_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("charging_points.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Dispenser delivering power",
    )

    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        doc="Session initiation timestamp",
    )

    end_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Session termination timestamp",
    )

    initial_meter_kwh: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        doc="Starting meter reading in kWh",
    )

    final_meter_kwh: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        doc="Closing meter reading in kWh",
    )

    total_energy_kwh: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        doc="Calculated energy delivered: final_meter - initial_meter",
    )

    total_cost: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        doc="Total billed cost: total_energy_kwh * price_per_kwh",
    )

    status: Mapped[str] = mapped_column(
        String(20),
        default="IN_PROGRESS",
        nullable=False,
        index=True,
        doc="Status: 'IN_PROGRESS', 'COMPLETED', 'STOPPED'",
    )

    # Relationships
    booking: Mapped[Optional["Booking"]] = relationship("Booking", back_populates="session", lazy="selectin")
    user: Mapped["User"] = relationship("User", lazy="selectin")
    charging_point: Mapped["ChargingPoint"] = relationship("ChargingPoint", lazy="selectin")
    payment: Mapped[Optional["Payment"]] = relationship(
        "Payment",
        back_populates="session",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<ChargingSession id={self.id} status={self.status} kwh={self.total_energy_kwh}>"
