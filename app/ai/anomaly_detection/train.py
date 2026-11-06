import os
import joblib
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, precision_score, recall_score, f1_score

from app.ai.anomaly_detection.telemetry_generator import (
    generate_telemetry_dataset,
    TELEMETRY_FEATURES,
)


def train_anomaly_detector(
    data_path: str = "ml_data/telemetry_data.csv",
    model_output_path: str = "ml_models/anomaly_detector.joblib",
    contamination: float = 0.06,
) -> dict:
    """
    Trains an unsupervised Isolation Forest model for EV charging dispenser anomaly detection.
    
    Why Isolation Forest?
    - Unsupervised: Hardware fault signatures and sensor failures do not need manual labeling in production.
    - Isolates outliers: Anomalies require fewer random splits in tree traversal than normal clustered points.
    - Real-time speed: Sub-millisecond inference time suitable for stream processing telemetry.
    """
    if not os.path.exists(data_path):
        print(f"Telemetry data not found at {data_path}. Generating dataset...")
        df = generate_telemetry_dataset(output_path=data_path, contamination=contamination)
    else:
        df = pd.read_csv(data_path)

    X_raw = df[TELEMETRY_FEATURES]
    y_ground_truth = df["is_anomaly"] if "is_anomaly" in df.columns else None

    # Step 1: Feature Standardization (Zero mean, unit variance)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_raw)

    # Step 2: Fit Isolation Forest
    iso_forest = IsolationForest(
        n_estimators=150,
        contamination=contamination,
        max_samples="auto",
        random_state=42,
        n_jobs=-1,
    )
    iso_forest.fit(X_scaled)

    # Step 3: Evaluate against ground truth (sklearn returns -1 for anomaly, +1 for normal)
    preds = iso_forest.predict(X_scaled)
    # Convert to binary: 1 for anomaly, 0 for normal
    y_pred_binary = np.where(preds == -1, 1, 0)

    metrics = {}
    if y_ground_truth is not None:
        precision = precision_score(y_ground_truth, y_pred_binary)
        recall = recall_score(y_ground_truth, y_pred_binary)
        f1 = f1_score(y_ground_truth, y_pred_binary)

        print("\n--- ISOLATION FOREST ANOMALY DETECTION EVALUATION ---")
        print(f"  Precision : {precision:.3f} (fraction of flagged points that were actual faults)")
        print(f"  Recall    : {recall:.3f} (fraction of actual faults correctly captured)")
        print(f"  F1-Score  : {f1:.3f}")
        print("\nDetailed Classification Breakdown:")
        print(classification_report(y_ground_truth, y_pred_binary, target_names=["Normal", "Anomaly"]))

        metrics = {
            "precision": round(float(precision), 3),
            "recall": round(float(recall), 3),
            "f1_score": round(float(f1), 3),
            "samples_evaluated": len(df),
            "anomalies_detected": int(np.sum(y_pred_binary)),
        }

    # Step 4: Serialize Model Bundle
    os.makedirs(os.path.dirname(model_output_path), exist_ok=True)
    bundle = {
        "model_version": "1.0.0-isolation-forest",
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "feature_names": TELEMETRY_FEATURES,
        "scaler": scaler,
        "model": iso_forest,
        "contamination": contamination,
        "metrics": metrics,
    }

    joblib.dump(bundle, model_output_path)
    print(f"\nAnomaly detection bundle successfully serialized to: {model_output_path}")
    return metrics


if __name__ == "__main__":
    train_anomaly_detector()

