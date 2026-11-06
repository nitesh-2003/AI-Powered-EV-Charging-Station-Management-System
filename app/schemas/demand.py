import uuid
from datetime import date
from typing import List, Optional, Dict
from pydantic import BaseModel, Field


class HourlyDemandForecast(BaseModel):
    """Hourly forecast prediction for a single station."""
    hour: int = Field(..., ge=0, le=23, description="Hour of the day (0-23)")
    time_label: str = Field(..., description="Human-readable hour (e.g. '08:00 - 09:00')")
    predicted_sessions: float = Field(..., ge=0.0, description="Predicted number of charging sessions")
    predicted_energy_kwh: float = Field(..., ge=0.0, description="Predicted total energy in kWh")
    demand_level: str = Field(..., description="Categorized demand level: LOW, MODERATE, PEAK, SURGE")


class DemandPredictionRequest(BaseModel):
    """Input payload to request charging demand forecasts for a station."""
    station_id: uuid.UUID = Field(..., description="Target charging station plaza UUID")
    target_date: date = Field(..., description="Date for which the demand forecast is requested")
    target_hour: Optional[int] = Field(None, ge=0, le=23, description="Optional single hour (0-23)")
    temperature_c: Optional[float] = Field(25.0, description="Forecasted ambient temperature in Celsius")


class DemandPredictionResponse(BaseModel):
    """Aggregated output response returned to the frontend/admin dashboard."""
    station_id: uuid.UUID
    station_name: str
    forecast_date: date
    hourly_forecast: List[HourlyDemandForecast]
    peak_hour: int
    peak_demand_level: str
    total_predicted_sessions: float
    total_predicted_energy_kwh: float
    model_version: str
    evaluation_metrics: Dict[str, float]

