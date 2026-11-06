import uuid
from typing import List, Optional, Dict
from pydantic import BaseModel, Field


class RecommendationRequest(BaseModel):
    """Driver criteria for finding the most optimal charging station."""
    user_latitude: float = Field(..., ge=-90.0, le=90.0, description="Driver GPS latitude")
    user_longitude: float = Field(..., ge=-180.0, le=180.0, description="Driver GPS longitude")
    battery_percentage: float = Field(..., ge=0.0, le=100.0, description="Current EV State of Charge (SOC %)")
    connector_type: Optional[str] = Field(None, description="Required plug standard: 'CCS2', 'TYPE2', 'CHADEMO'")
    min_power_kw: Optional[float] = Field(None, ge=0.0, description="Minimum acceptable charging power in kW")
    max_distance_km: Optional[float] = Field(50.0, ge=1.0, le=500.0, description="Search radius in kilometers")


class ScoredStationRecommendation(BaseModel):
    """Ranked station recommendation with transparent scoring breakdown."""
    rank: int
    station_id: uuid.UUID
    station_name: str
    address: str
    latitude: float
    longitude: float
    distance_km: float
    available_points: int
    total_points: int
    max_power_kw: float
    min_price_per_kwh: float
    compatible_connectors: List[str]
    recommendation_score: float = Field(..., ge=0.0, le=100.0, description="Overall score out of 100")
    score_breakdown: Dict[str, float]
    recommendation_reason: str


class RecommendationResponse(BaseModel):
    """List of ranked stations returned to driver."""
    total_found: int
    user_location: Dict[str, float]
    battery_soc_alert: Optional[str]
    recommendations: List[ScoredStationRecommendation]

