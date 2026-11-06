from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_active_user, require_admin
from app.models.user import User

from app.schemas.demand import DemandPredictionRequest, DemandPredictionResponse
from app.schemas.recommendation import RecommendationRequest, RecommendationResponse
from app.schemas.anomaly import (
    TelemetryReading,
    AnomalyDetectionResult,
    BatchTelemetryInspectionRequest,
    BatchTelemetryInspectionResponse,
)

from app.ai.demand_prediction.predictor import demand_predictor
from app.ai.recommendation.engine import StationRecommendationEngine
from app.ai.anomaly_detection.detector import anomaly_detector

router = APIRouter()


@router.post(
    "/predict-demand",
    response_model=DemandPredictionResponse,
    summary="Predict 24-hour charging demand for a station (AI Feature 1)",
)
def predict_charging_demand(
    request: DemandPredictionRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    """
    Supervised Machine Learning (Random Forest) predicting hourly session arrivals,
    energy demand (kWh), and peak congestion windows for a specified station.
    """
    return demand_predictor.predict_station_demand(db=db, request=request)


@router.post(
    "/recommend-stations",
    response_model=RecommendationResponse,
    summary="Recommend optimal stations using multi-factor ranking (AI Feature 2)",
)
def recommend_charging_stations(
    criteria: RecommendationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Adaptive multi-criteria ranking algorithm balancing distance (Haversine),
    real-time bay availability, charging power output, and electricity tariff rate.
    Prioritizes speed and distance automatically if driver's battery SOC is critical (<20%).
    """
    return StationRecommendationEngine.recommend(db=db, criteria=criteria)


@router.post(
    "/detect-anomalies",
    response_model=AnomalyDetectionResult,
    summary="Evaluate hardware dispenser telemetry for electrical/thermal anomalies (AI Feature 3)",
)
def detect_telemetry_anomaly(
    reading: TelemetryReading,
    current_admin: User = Depends(require_admin),
):
    """
    Unsupervised Isolation Forest evaluation combined with domain heuristics
    detecting voltage sags, overcurrent spikes, cable overheating, and meter glitches.
    """
    return anomaly_detector.inspect_reading(reading=reading)


@router.post(
    "/inspect-fleet-telemetry",
    response_model=BatchTelemetryInspectionResponse,
    summary="Batch inspect fleet telemetry streams across multiple chargers (AI Feature 3)",
)
def inspect_fleet_telemetry(
    request: BatchTelemetryInspectionRequest,
    current_admin: User = Depends(require_admin),
):
    """Batch evaluation of fleet-wide charging dispenser telemetry packets."""
    return anomaly_detector.inspect_batch(request=request)


@router.get(
    "/models-status",
    summary="Check status and evaluation metrics of trained ML models",
)
def get_ml_models_status(
    current_admin: User = Depends(require_admin),
):
    """Returns deployment status and validation metrics for active ML models."""
    return {
        "demand_forecaster": {
            "status": "LOADED" if demand_predictor.session_model else "UNAVAILABLE",
            "version": demand_predictor.version,
            "metrics": demand_predictor.metrics,
        },
        "recommendation_engine": {
            "status": "ACTIVE",
            "algorithm": "Adaptive Multi-Criteria Multi-Objective Scoring",
            "features_evaluated": ["haversine_distance", "availability_ratio", "max_power_kw", "tariff_price", "battery_soc_urgency"],
        },
        "anomaly_detector": {
            "status": "LOADED" if anomaly_detector.model else "UNAVAILABLE",
            "version": anomaly_detector.version,
            "features": anomaly_detector._bundle.get("feature_names", []),
            "metrics": anomaly_detector._bundle.get("metrics", {}),
        },
    }

