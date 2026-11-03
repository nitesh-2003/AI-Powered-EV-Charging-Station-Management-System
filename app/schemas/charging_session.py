import uuid
from decimal import Decimal
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.payment import PaymentResponse


class SessionStart(BaseModel):
    """Schema to start an EV charging session."""
    charging_point_id: uuid.UUID = Field(..., description="Charging dispenser ID")
    booking_id: Optional[uuid.UUID] = Field(None, description="Optional booking reference")
    initial_meter_kwh: Optional[Decimal] = Field(
        None,
        ge=0,
        description="Optional initial hardware meter reading (simulated if omitted)",
    )


class SessionStop(BaseModel):
    """Schema to stop an ongoing charging session."""
    final_meter_kwh: Optional[Decimal] = Field(
        None,
        ge=0,
        description="Optional final hardware meter reading (simulated if omitted)",
    )


class SessionResponse(BaseModel):
    """Schema for charging session progress, completion, and cost breakdown."""
    id: uuid.UUID
    user_id: uuid.UUID
    charging_point_id: uuid.UUID
    booking_id: Optional[uuid.UUID]
    start_time: datetime
    end_time: Optional[datetime]
    initial_meter_kwh: Decimal
    final_meter_kwh: Optional[Decimal]
    total_energy_kwh: Optional[Decimal]
    total_cost: Optional[Decimal]
    status: str
    created_at: datetime
    payment: Optional[PaymentResponse] = None

    model_config = ConfigDict(from_attributes=True)
