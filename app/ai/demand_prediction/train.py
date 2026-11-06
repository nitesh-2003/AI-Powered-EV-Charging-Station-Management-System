import os
import joblib
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from sklearn.ensemble import RandomForestRegressor
from sklearn.dummy import DummyRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from app.ai.demand_prediction.dataset_generator import generate_historical_charging_dataset
from app.ai.demand_prediction.features import (
    engineer_demand_features,
    chronological_train_test_split,
    FEATURE_COLUMNS,
    TARGET_SESSIONS,
    TARGET_ENERGY,
)


def train_demand_forecaster(
    data_path: str = "ml_data/historical_demand.csv",
    model_output_path: str = "ml_models/demand_forecaster.joblib",
) -> dict:
    """
    Executes the complete machine learning training pipeline:
    1. Loads or generates historical EV charging time-series data.
    2. Performs feature engineering (cyclical encodings, weather interaction).
    3. Splits data chronologically (80% train / 20% test) to prevent future data leakage.
    4. Evaluates a Dummy Baseline against Random Forest Regressor.
    5. Computes production metrics: MAE, RMSE, and R².
    6. Serializes model artifact bundle to disk.
    """
    # Step 1: Ensure dataset exists
    if not os.path.exists(data_path):
        print(f"Dataset not found at {data_path}. Generating synthetic historical records...")
        df = generate_historical_charging_dataset(output_path=data_path, num_days=120)
    else:
        df = pd.read_csv(data_path)

    print(f"Dataset loaded: {len(df):,} total hourly observations across {df['station_id'].nunique()} stations.")

    # Step 2: Engineer features
    data = engineer_demand_features(df)

    # Step 3: Chronological Train / Test Split
    train_df, test_df = chronological_train_test_split(data, test_ratio=0.20)
    print(f"Train split: {len(train_df):,} samples | Test split: {len(test_df):,} samples (chronological)")

    X_train = train_df[FEATURE_COLUMNS]
    y_train_sessions = train_df[TARGET_SESSIONS]
    y_train_energy = train_df[TARGET_ENERGY]

    X_test = test_df[FEATURE_COLUMNS]
    y_test_sessions = test_df[TARGET_SESSIONS]
    y_test_energy = test_df[TARGET_ENERGY]

    # Step 4: Baseline Model Benchmark
    baseline_sessions = DummyRegressor(strategy="mean")
    baseline_sessions.fit(X_train, y_train_sessions)
    base_preds = baseline_sessions.predict(X_test)

    base_mae = mean_absolute_error(y_test_sessions, base_preds)
    base_rmse = np.sqrt(mean_squared_error(y_test_sessions, base_preds))
    base_r2 = r2_score(y_test_sessions, base_preds)

    print("\n--- BASELINE MODEL PERFORMANCE (Predicting Mean) ---")
    print(f"  MAE  : {base_mae:.3f} sessions")
    print(f"  RMSE : {base_rmse:.3f} sessions")
    print(f"  R²   : {base_r2:.3f}")

    # Step 5: Train Random Forest Regressor for Sessions
    rf_sessions = RandomForestRegressor(
        n_estimators=100,
        max_depth=12,
        min_samples_split=4,
        random_state=42,
        n_jobs=-1,
    )
    rf_sessions.fit(X_train, y_train_sessions)
    rf_session_preds = rf_sessions.predict(X_test)

    rf_mae = mean_absolute_error(y_test_sessions, rf_session_preds)
    rf_rmse = np.sqrt(mean_squared_error(y_test_sessions, rf_session_preds))
    rf_r2 = r2_score(y_test_sessions, rf_session_preds)

    # Step 6: Train Random Forest Regressor for Energy Consumption (kWh)
    rf_energy = RandomForestRegressor(
        n_estimators=100,
        max_depth=12,
        min_samples_split=4,
        random_state=42,
        n_jobs=-1,
    )
    rf_energy.fit(X_train, y_train_energy)
    rf_energy_preds = rf_energy.predict(X_test)

    energy_mae = mean_absolute_error(y_test_energy, rf_energy_preds)
    energy_rmse = np.sqrt(mean_squared_error(y_test_energy, rf_energy_preds))
    energy_r2 = r2_score(y_test_energy, rf_energy_preds)

    print("\n--- RANDOM FOREST REGRESSOR PERFORMANCE ---")
    print(f"  Sessions MAE  : {rf_mae:.3f} sessions  (Error reduced by {(1 - rf_mae / base_mae) * 100:.1f}%)")
    print(f"  Sessions RMSE : {rf_rmse:.3f} sessions")
    print(f"  Sessions R²   : {rf_r2:.3f}")
    print(f"  Energy MAE    : {energy_mae:.2f} kWh")
    print(f"  Energy RMSE   : {energy_rmse:.2f} kWh")
    print(f"  Energy R²     : {energy_r2:.3f}")

    # Step 7: Serialize Model Bundle
    os.makedirs(os.path.dirname(model_output_path), exist_ok=True)
    bundle = {
        "model_version": "1.0.0-rf",
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "feature_columns": FEATURE_COLUMNS,
        "session_model": rf_sessions,
        "energy_model": rf_energy,
        "evaluation_metrics": {
            "baseline_mae": round(float(base_mae), 3),
            "baseline_rmse": round(float(base_rmse), 3),
            "baseline_r2": round(float(base_r2), 3),
            "sessions_mae": round(float(rf_mae), 3),
            "sessions_rmse": round(float(rf_rmse), 3),
            "sessions_r2": round(float(rf_r2), 3),
            "energy_mae": round(float(energy_mae), 2),
            "energy_rmse": round(float(energy_rmse), 2),
            "energy_r2": round(float(energy_r2), 2),
        },
    }

    joblib.dump(bundle, model_output_path)
    print(f"\nModel artifact successfully saved to: {model_output_path}")
    return bundle["evaluation_metrics"]


if __name__ == "__main__":
    train_demand_forecaster()

