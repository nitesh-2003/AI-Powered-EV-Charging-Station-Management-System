import os
import joblib
import uuid
from datetime import date
from typing import Optional, List, Dict
import pandas as pd
from sqlalchemy.orm import Session

from app.models.station import ChargingStation
from app.schemas.demand import (
    DemandPredictionRequest,
    DemandPredictionResponse,
    HourlyDemandForecast,
)
from app.ai.demand_prediction.features import engineer_demand_features, FEATURE_COLUMNS


class DemandPredictor:
    """
    Inference service that loads the trained demand forecasting model
    and generates 24-hour demand projections for charging stations.
    """
    _instance = None
    _model_bundle = None

    def __init__(self, model_path: str = "ml_models/demand_forecaster.joblib"):
        self.model_path = model_path
        self._load_model()

    def _load_model(self):
        if not os.path.exists(self.model_path):
            from app.ai.demand_prediction.train import train_demand_forecaster
            print(f"Model artifact not found at {self.model_path}. Initiating training pipeline...")
            train_demand_forecaster(model_output_path=self.model_path)

        self._model_bundle = joblib.load(self.model_path)
        self.session_model = self._model_bundle["session_model"]
        self.energy_model = self._model_bundle["energy_model"]
        self.version = self._model_bundle.get("model_version", "1.0.0")
        self.metrics = self._model_bundle.get("evaluation_metrics", {})

    def predict_station_demand(
        self,
        db: Session,
        request: DemandPredictionRequest,
    ) -> DemandPredictionResponse:
        """
        Generates 24-hour forecasted demand for a given charging station on a specific date.
        """
        # Fetch station details
        station = db.query(ChargingStation).filter(ChargingStation.id == request.station_id).first()
        station_name = station.name if station else "Charging Station Hub"
        dispenser_count = len(station.charging_points) if station and station.charging_points else 8

        target_date = request.target_date
        day_of_week = target_date.weekday()
        is_weekend = 1 if day_of_week in [5, 6] else 0

        # Construct 24 hourly rows
        hours = range(24) if request.target_hour is None else [request.target_hour]
        rows = []
        for h in hours:
            rows.append({
                "station_id": str(request.station_id),
                "station_name": station_name,
                "station_type": "URBAN_COMMUTER",
                "total_dispensers": dispenser_count,
                "hour_of_day": h,
                "day_of_week": day_of_week,
                "is_weekend": is_weekend,
                "temperature_c": request.temperature_c or 24.0,
            })

        df_input = pd.DataFrame(rows)
        df_feat = engineer_demand_features(df_input)
        X = df_feat[FEATURE_COLUMNS]

        # Generate ML predictions
        pred_sessions = self.session_model.predict(X)
        pred_energy = self.energy_model.predict(X)

        hourly_forecasts: List[HourlyDemandForecast] = []
        total_sessions = 0.0
        total_energy = 0.0
        peak_hour = 0
        max_sessions = -1.0

        for i, h in enumerate(hours):
            sessions = round(max(0.0, float(pred_sessions[i])), 1)
            # Cannot exceed physical dispenser count
            sessions = min(sessions, float(dispenser_count))
            energy = round(max(0.0, float(pred_energy[i])), 1)

            total_sessions += sessions
            total_energy += energy

            if sessions > max_sessions:
                max_sessions = sessions
                peak_hour = h

            # Classify demand intensity relative to dispenser capacity
            ratio = sessions / max(1, dispenser_count)
            if ratio >= 0.85:
                level = "SURGE"
            elif ratio >= 0.60:
                level = "PEAK"
            elif ratio >= 0.25:
                level = "MODERATE"
            else:
                level = "LOW"

            time_label = f"{h:02d}:00 - {(h + 1) % 24:02d}:00"
            hourly_forecasts.append(
                HourlyDemandForecast(
                    hour=h,
                    time_label=time_label,
                    predicted_sessions=sessions,
                    predicted_energy_kwh=energy,
                    demand_level=level,
                )
            )

        # Categorize overall peak demand level
        peak_ratio = max_sessions / max(1, dispenser_count)
        if peak_ratio >= 0.85:
            peak_demand_level = "SURGE"
        elif peak_ratio >= 0.60:
            peak_demand_level = "PEAK"
        elif peak_ratio >= 0.25:
            peak_demand_level = "MODERATE"
        else:
            peak_demand_level = "LOW"

        return DemandPredictionResponse(
            station_id=request.station_id,
            station_name=station_name,
            forecast_date=target_date,
            hourly_forecast=hourly_forecasts,
            peak_hour=peak_hour,
            peak_demand_level=peak_demand_level,
            total_predicted_sessions=round(total_sessions, 1),
            total_predicted_energy_kwh=round(total_energy, 1),
            model_version=self.version,
            evaluation_metrics=self.metrics,
        )


# Singleton instance
demand_predictor = DemandPredictor()

