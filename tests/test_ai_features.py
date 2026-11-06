import uuid
import pytest
from datetime import date, timedelta

from app.schemas.anomaly import TelemetryReading
from app.schemas.recommendation import RecommendationRequest
from app.schemas.demand import DemandPredictionRequest
from app.ai.anomaly_detection.detector import anomaly_detector
from app.ai.recommendation.engine import StationRecommendationEngine, haversine_distance_km
from app.ai.demand_prediction.predictor import demand_predictor
from app.api.v1.endpoints.ai import (
    predict_charging_demand,
    recommend_charging_stations,
    detect_telemetry_anomaly,
    get_ml_models_status,
)


def test_haversine_distance():
    """Verify accuracy of Haversine distance calculation."""
    # Distance between San Francisco (37.7749, -122.4194) and Oakland (37.8044, -122.2712) ~ 13.5 km
    dist = haversine_distance_km(37.7749, -122.4194, 37.8044, -122.2712)
    assert 12.0 <= dist <= 15.0


def test_isolation_forest_anomaly_detection_signatures():
    """Verify that normal charging is categorized as normal and severe faults trigger alerts."""
    dummy_point_id = uuid.uuid4()

    # 1. Normal charging packet
    normal_reading = TelemetryReading(
        charging_point_id=dummy_point_id,
        voltage_v=400.0,
        current_a=150.0,
        power_kw=60.0,
        battery_soc_pct=50.0,
        charging_duration_minutes=25.0,
        energy_consumed_kwh=25.0,
        temperature_c=38.0,
    )
    result_normal = anomaly_detector.inspect_reading(normal_reading)
    assert not result_normal.is_anomaly or result_normal.severity == "NORMAL"

    # 2. Critical Overheating packet
    fault_reading = TelemetryReading(
        charging_point_id=dummy_point_id,
        voltage_v=395.0,
        current_a=220.0,
        power_kw=86.9,
        battery_soc_pct=65.0,
        charging_duration_minutes=35.0,
        energy_consumed_kwh=40.0,
        temperature_c=88.5,  # DANGEROUS OVERHEATING
    )
    result_fault = anomaly_detector.inspect_reading(fault_reading)
    assert result_fault.is_anomaly
    assert result_fault.severity == "CRITICAL"
    assert "CRITICAL OVERHEATING" in result_fault.detected_irregularities[0]


def test_station_recommendation_multi_criteria_ranking():
    """Verify adaptive multi-criteria scoring algorithm and battery SOC urgency."""
    class MockPoint:
        def __init__(self, conn, kw, status, price):
            self.id = uuid.uuid4()
            self.connector_type = conn
            self.power_kw = kw
            self.status = status
            self.price_per_kwh = price

    class MockStation:
        def __init__(self, name, lat, lon, points):
            self.id = uuid.uuid4()
            self.name = name
            self.address = "Test Street"
            self.latitude = lat
            self.longitude = lon
            self.status = "ACTIVE"
            self.charging_points = points

    class MockDB:
        def query(self, model):
            class Q:
                def filter(self, *a):
                    return self
                def all(self):
                    return [
                        MockStation(
                            "Close Plaza",
                            37.7750,
                            -122.4190,
                            [MockPoint("CCS2", 150.0, "AVAILABLE", 20.0)],
                        ),
                        MockStation(
                            "Far Plaza",
                            37.8500,
                            -122.3000,
                            [MockPoint("CCS2", 50.0, "OCCUPIED", 25.0)],
                        ),
                    ]
            return Q()

    db = MockDB()

    # Normal battery request (50% SOC)
    req_normal = RecommendationRequest(
        user_latitude=37.7749,
        user_longitude=-122.4194,
        battery_percentage=50.0,
        max_distance_km=50.0,
    )
    res_normal = StationRecommendationEngine.recommend(db=db, criteria=req_normal)
    assert res_normal.total_found == 2
    assert res_normal.recommendations[0].station_name == "Close Plaza"
    assert res_normal.recommendations[0].recommendation_score > res_normal.recommendations[1].recommendation_score

    # Critical battery request (12% SOC)
    req_critical = RecommendationRequest(
        user_latitude=37.7749,
        user_longitude=-122.4194,
        battery_percentage=12.0,
        max_distance_km=50.0,
    )
    res_critical = StationRecommendationEngine.recommend(db=db, criteria=req_critical)
    assert res_critical.battery_soc_alert is not None
    assert "CRITICAL BATTERY" in res_critical.battery_soc_alert


def test_demand_prediction_24h_cycle():
    """Verify that demand forecasting produces 24 hourly predictions with realistic properties."""
    class MockPoint:
        def __init__(self):
            self.id = uuid.uuid4()

    class MockStation:
        def __init__(self):
            self.id = uuid.uuid4()
            self.name = "Central Metro Hub"
            self.charging_points = [MockPoint() for _ in range(10)]

    class MockDB:
        def query(self, model):
            class Q:
                def filter(self, *a):
                    return self
                def first(self):
                    return MockStation()
            return Q()

    db = MockDB()
    target_date = date.today() + timedelta(days=1)
    req = DemandPredictionRequest(
        station_id=uuid.uuid4(),
        target_date=target_date,
        temperature_c=25.0,
    )

    res = demand_predictor.predict_station_demand(db=db, request=req)
    assert res.station_name == "Central Metro Hub"
    assert len(res.hourly_forecast) == 24
    assert res.total_predicted_sessions >= 0.0
    assert res.total_predicted_energy_kwh >= 0.0
    assert res.peak_demand_level in ["LOW", "MODERATE", "PEAK", "SURGE"]
    assert res.model_version == "1.0.0-rf"


def test_ai_endpoints_dispatch():
    """Verify endpoint handlers directly with mocked permissions and database."""
    models_status = get_ml_models_status(current_admin=None)
    assert models_status["demand_forecaster"]["status"] == "LOADED"
    assert models_status["anomaly_detector"]["status"] == "LOADED"
    assert models_status["recommendation_engine"]["status"] == "ACTIVE"

    # Test Anomaly Endpoint
    anomaly_reading = TelemetryReading(
        charging_point_id=uuid.uuid4(),
        voltage_v=280.0,  # VOLTAGE SAG
        current_a=330.0,  # OVERCURRENT
        power_kw=92.4,
        battery_soc_pct=50.0,
        charging_duration_minutes=20.0,
        energy_consumed_kwh=30.0,
        temperature_c=50.0,
    )
    res = detect_telemetry_anomaly(reading=anomaly_reading, current_admin=None)
    assert res.is_anomaly is True
    assert res.severity in ["HIGH", "CRITICAL"]
