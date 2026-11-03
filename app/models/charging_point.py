import uuid
from decimal import Decimal
from typing import TYPE_CHECKING
from sqlalchemy import String, Float, Numeric, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import TimestampedModel

if TYPE_CHECKING:
    from app.models.station import ChargingStation


class ChargingPoint(TimestampedModel):
    """
    Individual charging dispenser (EVSE) located at a station.
    """
    __tablename__ = "charging_points"

    station_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("charging_stations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Reference to parent ChargingStation",
    )

    identifier: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="Physical dispenser tag (e.g. 'BAY-1', 'FAST-02')",
    )

    connector_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        doc="Connector standard: 'CCS2', 'TYPE2', or 'CHADEMO'",
    )

    power_kw: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        doc="Maximum charging power output in kilowatts (e.g., 22.0, 50.0, 150.0)",
    )

    status: Mapped[str] = mapped_column(
        String(20),
        default="AVAILABLE",
        nullable=False,
        doc="Operational state: 'AVAILABLE', 'OCCUPIED', 'RESERVED', or 'FAULTED'",
    )

    price_per_kwh: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        doc="Tariff rate per kilowatt-hour in local currency units",
    )

    # Many-to-One relationship back to parent station
    station: Mapped["ChargingStation"] = relationship(
        "ChargingStation",
        back_populates="charging_points",
    )

    def __repr__(self) -> str:
        return f"<ChargingPoint id={self.id} identifier={self.identifier} status={self.status}>"

