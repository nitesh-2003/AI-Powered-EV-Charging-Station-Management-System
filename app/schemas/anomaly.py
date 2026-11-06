import uuid
from datetime import datetime
from typing import List, Optional, Dict
from pydantic import BaseModel, Field


class TelemetryReading(BaseModel):
    """Real-time or simulated hardware dispenser telemetry packet."""
    charging_point_id: uuid.UUID = Field(..., description="Dispenser hardware ID")
    session_id: Optional[uuid.UUID] = Field(None, description="Active session ID if charging")
    voltage_v: float = Field(..., ge=0.0, le=1000.0, description="Bus voltage in Volts (nominal: 400V or 800V)")
    current_a: float = Field(..., ge=0.0, le=600.0, description="Current flow in Amperes")
    power_kw: float = Field(..., ge=0.0, le=400.0, description="Delivered power in kW")
    battery_soc_pct: float = Field(..., ge=0.0, le=100.0, description="Vehicle battery state of charge (0-100%)")
    charging_duration_minutes: float = Field(..., ge=0.0, description="Elapsed minutes of power delivery")
    energy_consumed_kwh: float = Field(..., ge=0.0, description="Cumulative kWh delivered in session")
    temperature_c: Optional[float] = Field(35.0, description="Dispenser plug / cable temperature")


class AnomalyDetectionResult(BaseModel):
    """Result of Isolation Forest evaluation on a telemetry reading."""
    charging_point_id: uuid.UUID
    is_anomaly: bool
    anomaly_score: float = Field(..., description="Anomaly score (-1.0 to 1.0; values < 0 denote anomalies)")
    confidence_pct: float = Field(..., ge=0.0, le=100.0, description="Anomaly confidence percentage")
    severity: str = Field(..., description="'NORMAL', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'")
    detected_irregularities: List[str]
    recommended_action: str
    evaluated_at: datetime


class BatchTelemetryInspectionRequest(BaseModel):
    """Batch payload of telemetry readings for fleet-wide inspection."""
    readings: List[TelemetryReading]


class BatchTelemetryInspectionResponse(BaseModel):
    """Aggregated response of fleet-wide telemetry analysis."""
    total_evaluated: int
    anomalies_detected: int
    critical_alerts: int
    results: List[AnomalyDetectionResult]

