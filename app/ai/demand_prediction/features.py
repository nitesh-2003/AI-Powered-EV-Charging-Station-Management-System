import numpy as np
import pandas as pd
from typing import Tuple, List


FEATURE_COLUMNS = [
    "hour_of_day",
    "hour_sin",
    "hour_cos",
    "day_of_week",
    "dow_sin",
    "dow_cos",
    "is_weekend",
    "temperature_c",
    "total_dispensers",
    "is_urban",
    "is_highway",
    "is_retail",
    "is_transit",
]

TARGET_SESSIONS = "charging_sessions"
TARGET_ENERGY = "total_energy_kwh"


def engineer_demand_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Transforms raw timestamped records into machine learning feature matrices.
    Applies cyclical trigonometry transformations to preserve diurnal and weekly continuity.
    """
    data = df.copy()

    # Cyclical hour encoding (ensures hour 23 and hour 0 are mathematically continuous)
    data["hour_sin"] = np.sin(2 * np.pi * data["hour_of_day"] / 24.0)
    data["hour_cos"] = np.cos(2 * np.pi * data["hour_of_day"] / 24.0)

    # Cyclical day-of-week encoding
    data["dow_sin"] = np.sin(2 * np.pi * data["day_of_week"] / 7.0)
    data["dow_cos"] = np.cos(2 * np.pi * data["day_of_week"] / 7.0)

    # One-hot encode station category
    st_type = data.get("station_type", "")
    data["is_urban"] = (st_type == "URBAN_COMMUTER").astype(int)
    data["is_highway"] = (st_type == "HIGHWAY_CORRIDOR").astype(int)
    data["is_retail"] = (st_type == "RETAIL_DESTINATION").astype(int)
    data["is_transit"] = (st_type == "FLEET_TRANSIT").astype(int)

    return data


def chronological_train_test_split(
    df: pd.DataFrame,
    test_ratio: float = 0.20,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Splits sequential time-series observations chronologically.
    Guarantees zero data leakage by keeping the latest time window exclusively for testing.
    """
    sorted_df = df.sort_values(by="timestamp").reset_index(drop=True)
    split_idx = int(len(sorted_df) * (1.0 - test_ratio))

    train_df = sorted_df.iloc[:split_idx].copy()
    test_df = sorted_df.iloc[split_idx:].copy()

    return train_df, test_df

