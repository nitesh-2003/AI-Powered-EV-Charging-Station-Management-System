import uuid
from decimal import Decimal
from typing import TYPE_CHECKING
from sqlalchemy import String, Numeric, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import TimestampedModel

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.charging_session import ChargingSession


class Payment(TimestampedModel):
    """
    Simulated financial transaction record generated for completed charging sessions.
    """
    __tablename__ = "payments"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("charging_sessions.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
        doc="One-to-One link with charged session",
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Payer account",
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        doc="Total billed amount",
    )

    status: Mapped[str] = mapped_column(
        String(20),
        default="COMPLETED",
        nullable=False,
        doc="Payment state: 'PENDING', 'COMPLETED', 'FAILED'",
    )

    transaction_ref: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        doc="Simulated payment gateway transaction reference (e.g., 'SIM-PAY-98124')",
    )

    # Relationships
    session: Mapped["ChargingSession"] = relationship("ChargingSession", back_populates="payment")
    user: Mapped["User"] = relationship("User", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Payment id={self.id} amount={self.amount} status={self.status}>"

