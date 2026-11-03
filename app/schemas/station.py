import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.charging_point import ChargingPointResponse


class StationBase(BaseModel):
    """Base shared attributes for a charging station plaza."""
    name: str = Field(..., min_length=2, max_length=100, description="Station name")
    address: str = Field(..., min_length=5, max_length=255, description="Physical address")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Valid latitude between -90 and 90")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Valid longitude between -180 and 180")
    status: str = Field(default="ACTIVE", description="'ACTIVE', 'INACTIVE', or 'UNDER_MAINTENANCE'")


class StationCreate(StationBase):
    """Schema for creating a new charging station plaza."""
    pass


class StationUpdate(BaseModel):
    """Schema for updating station information."""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    address: Optional[str] = Field(None, min_length=5, max_length=255)
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)
    status: Optional[str] = None


class StationResponse(StationBase):
    """Schema for returning station information along with nested charging points."""
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    charging_points: List[ChargingPointResponse] = []

    model_config = ConfigDict(from_attributes=True)
