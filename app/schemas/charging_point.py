import uuid
from decimal import Decimal
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class ChargingPointBase(BaseModel):
    """Base shared attributes for a charging dispenser (EVSE)."""
    identifier: str = Field(..., min_length=1, max_length=50, description="Dispenser tag (e.g. 'BAY-01')")
    connector_type: str = Field(..., description="Connector standard: 'CCS2', 'TYPE2', or 'CHADEMO'")
    power_kw: float = Field(..., gt=0, description="Max power output in kW (must be positive)")
    status: str = Field(default="AVAILABLE", description="'AVAILABLE', 'OCCUPIED', 'RESERVED', 'FAULTED'")
    price_per_kwh: Decimal = Field(..., ge=0, description="Tariff price per kWh")


class ChargingPointCreate(ChargingPointBase):
    """Schema for adding a charging dispenser to a station."""
    pass


class ChargingPointUpdate(BaseModel):
    """Schema for updating dispenser status or tariff."""
    identifier: Optional[str] = Field(None, min_length=1, max_length=50)
    connector_type: Optional[str] = None
    power_kw: Optional[float] = Field(None, gt=0)
    status: Optional[str] = None
    price_per_kwh: Optional[Decimal] = Field(None, ge=0)


class ChargingPointResponse(ChargingPointBase):
    """Schema for returning charging point details."""
    id: uuid.UUID
    station_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

