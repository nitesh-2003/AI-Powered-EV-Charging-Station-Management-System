import os
import joblib
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from typing import List, Dict, Tuple

from app.schemas.anomaly import (
    TelemetryReading,
    AnomalyDetectionResult,
    BatchTelemetryInspectionRequest,
    BatchTelemetryInspectionResponse,
)
from app.ai.anomaly_detection.telemetry_generator import TELEMETRY_FEATURES


class AnomalyDetector:
    """
    Inference service for real-time hardware telemetry anomaly inspection.
    Combines unsupervised Isolation Forest outlier scoring with deterministic
    EV engineering rule heuristics for explainable root-cause diagnosis.
    """
    _instance = None
    _bundle = None

    def __init__(self, model_path: str = "ml_models/anomaly_detector.joblib"):
        self.model_path = model_path
        self._load_model()

    def _load_model(self):
        if not os.path.exists(self.model_path):
            from app.ai.anomaly_detection.train import train_anomaly_detector
            print(f"Model artifact not found at {self.model_path}. Initiating training...")
            train_anomaly_detector(model_output_path=self.model_path)

        self._bundle = joblib.load(self.model_path)
        self.model = self._bundle["model"]
        self.scaler = self._bundle["scaler"]
        self.version = self._bundle.get("model_version", "1.0.0")

    def inspect_reading(self, reading: TelemetryReading) -> AnomalyDetectionResult:
        """
        Evaluates a single telemetry reading packet.
        """
        row = {
            "voltage_v": reading.voltage_v,
            "current_a": reading.current_a,
            "power_kw": reading.power_kw,
            "battery_soc_pct": reading.battery_soc_pct,
            "charging_duration_minutes": reading.charging_duration_minutes,
            "energy_consumed_kwh": reading.energy_consumed_kwh,
            "temperature_c": reading.temperature_c if reading.temperature_c is not None else 35.0,
        }

        # Standardize features with proper feature names
        df_row = pd.DataFrame([row])
        scaled = self.scaler.transform(df_row)
        # decision_function: < 0 is anomaly, >= 0 is normal
        score = float(self.model.decision_function(scaled)[0])
        is_anomaly_model = score < 0.0

        # Engineering heuristics for root cause diagnosis & severity
        irregularities = []
        severity = "NORMAL"
        action = "Hardware metrics nominal. Continue standard charging operation."

        # Rule 1: Thermal limits
        if reading.temperature_c and reading.temperature_c >= 78.0:
            irregularities.append(f"CRITICAL OVERHEATING: Cable temperature at {reading.temperature_c:.1f}°C (Safe limit: < 75°C).")
            severity = "CRITICAL"
            action = "EMERGENCY POWER CUTOFF: Dispatch technician to inspect liquid cooling pump."

        # Rule 2: Voltage Sag / Grid instability
        if reading.voltage_v < 330.0:
            irregularities.append(f"VOLTAGE SAG: Bus voltage collapsed to {reading.voltage_v:.1f}V (Nominal: 380V-420V).")
            if severity != "CRITICAL":
                severity = "HIGH"
                action = "Throttle charging current to protect vehicle on-board charger."

        # Rule 3: Overcurrent
        if reading.current_a > 320.0:
            irregularities.append(f"OVERCURRENT EXCEEDED: Amperage spiked to {reading.current_a:.1f}A.")
            if severity != "CRITICAL":
                severity = "HIGH"
                action = "Reduce power delivery setpoint and check contactor resistance."

        # Rule 4: Meter / Telemetry Glitch
        if reading.charging_duration_minutes > 5.0 and reading.power_kw > 10.0 and reading.energy_consumed_kwh <= 0.1:
            irregularities.append("METER FREEZE: Power flow active but energy accumulator reading 0.00 kWh.")
            if severity not in ["CRITICAL", "HIGH"]:
                severity = "MEDIUM"
                action = "Reboot meter telemetry gateway; flag session for manual billing audit."

        # Rule 5: BMS CC/CV Taper violation
        if reading.battery_soc_pct >= 90.0 and reading.power_kw > 90.0:
            irregularities.append(f"BMS PROTOCOL VIOLATION: Excessive power ({reading.power_kw:.1f}kW) delivered at {reading.battery_soc_pct:.1f}% SOC.")
            if severity not in ["CRITICAL", "HIGH"]:
                severity = "HIGH"
                action = "Enforce CCS2 tapering profile; signal BMS power step-down."

        # Final anomaly status: triggered by Isolation Forest or critical rule
        is_anomaly = is_anomaly_model or len(irregularities) > 0

        # Calculate confidence percentage
        if is_anomaly:
            if severity == "CRITICAL":
                confidence = 98.5
            elif severity == "HIGH":
                confidence = 92.0
            else:
                confidence = min(95.0, max(50.0, 50.0 + abs(score) * 200.0))
        else:
            confidence = min(99.0, max(60.0, 50.0 + score * 150.0))

        return AnomalyDetectionResult(
            charging_point_id=reading.charging_point_id,
            is_anomaly=is_anomaly,
            anomaly_score=round(score, 4),
            confidence_pct=round(confidence, 1),
            severity=severity,
            detected_irregularities=irregularities,
            recommended_action=action,
            evaluated_at=datetime.now(timezone.utc),
        )

    def inspect_batch(self, request: BatchTelemetryInspectionRequest) -> BatchTelemetryInspectionResponse:
        """Evaluates a batch of telemetry packets across multiple dispensers."""
        results = [self.inspect_reading(r) for r in request.readings]
        anomalies = sum(1 for r in results if r.is_anomaly)
        criticals = sum(1 for r in results if r.severity in ["HIGH", "CRITICAL"])

        return BatchTelemetryInspectionResponse(
            total_evaluated=len(results),
            anomalies_detected=anomalies,
            critical_alerts=criticals,
            results=results,
        )


# Singleton instance
anomaly_detector = AnomalyDetector()
