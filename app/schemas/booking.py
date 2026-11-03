import uuid
from datetime import datetime
from pydantic import BaseModel, Field, model_validator, ConfigDict


class BookingCreate(BaseModel):
    """Schema for reserving a charging time slot."""
    charging_point_id: uuid.UUID = Field(..., description="Target charging dispenser ID")
    start_time: datetime = Field(..., description="Reservation start timestamp (ISO 8601)")
    end_time: datetime = Field(..., description="Reservation end timestamp (ISO 8601)")

    @model_validator(mode="after")
    def validate_time_range(self) -> "BookingCreate":
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be strictly after start_time")
        return self


class BookingResponse(BaseModel):
    """Schema for booking confirmation and details."""
    id: uuid.UUID
    user_id: uuid.UUID
    charging_point_id: uuid.UUID
    start_time: datetime
    end_time: datetime
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
