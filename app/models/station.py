from typing import List, TYPE_CHECKING
from sqlalchemy import String, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import TimestampedModel

if TYPE_CHECKING:
    from app.models.charging_point import ChargingPoint


class ChargingStation(TimestampedModel):
    """
    Physical charging plaza or station facility containing one or more charging points.
    """
    __tablename__ = "charging_stations"

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        doc="Name of the charging station plaza (e.g., 'Downtown Fast Charging Hub')",
    )

    address: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Physical street address or landmark",
    )

    latitude: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        doc="GPS Latitude coordinate for maps and distance calculation",
    )

    longitude: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        doc="GPS Longitude coordinate for maps and distance calculation",
    )

    status: Mapped[str] = mapped_column(
        String(20),
        default="ACTIVE",
        nullable=False,
        doc="Operational status: 'ACTIVE', 'INACTIVE', or 'UNDER_MAINTENANCE'",
    )

    # One-to-Many relationship with ChargingPoint
    charging_points: Mapped[List["ChargingPoint"]] = relationship(
        "ChargingPoint",
        back_populates="station",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<ChargingStation id={self.id} name={self.name} status={self.status}>"

