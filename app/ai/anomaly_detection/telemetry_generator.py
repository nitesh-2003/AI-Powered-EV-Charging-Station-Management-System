import os
import numpy as np
import pandas as pd


TELEMETRY_FEATURES = [
    "voltage_v",
    "current_a",
    "power_kw",
    "battery_soc_pct",
    "charging_duration_minutes",
    "energy_consumed_kwh",
    "temperature_c",
]


def generate_telemetry_dataset(
    output_path: str = "ml_data/telemetry_data.csv",
    num_samples: int = 5000,
    contamination: float = 0.06,  # 6% genuine anomalies
    seed: int = 42,
) -> pd.DataFrame:
    """
    Generates realistic EV charging telemetry containing both normal CC-CV charging curves
    and distinct hardware/electrical anomaly signatures:
    - Normal: Constant current bulk charging (10-80% SOC) and tapering phase (80-100% SOC).
    - Anomalies: Voltage sags, current spikes, thermal overheating, sensor stalls, BMS protocol violations.
    """
    np.random.seed(seed)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    n_normal = int(num_samples * (1.0 - contamination))
    n_anomaly = num_samples - n_normal

    normal_records = []
    for _ in range(n_normal):
        soc = np.random.uniform(10.0, 98.0)
        duration = np.random.uniform(5.0, 75.0)

        # Constant Current vs Tapering
        if soc < 80.0:
            # Bulk fast-charge phase
            voltage = np.random.normal(400.0, 6.0)
            current = np.random.normal(150.0, 15.0)
        else:
            # Tapering phase near 100% SOC
            taper_factor = (100.0 - soc) / 20.0
            voltage = np.random.normal(415.0, 5.0)
            current = max(10.0, np.random.normal(80.0 * taper_factor, 8.0))

        # P = V * I / 1000
        power_kw = (voltage * current) / 1000.0
        # Energy = average power * hours
        energy_kwh = max(0.5, (power_kw * (duration / 60.0)) * np.random.uniform(0.9, 1.05))
        # Cable temperature normal operating range (30C to 52C)
        temp_c = 32.0 + (power_kw / 150.0) * 18.0 + np.random.normal(0, 2.0)

        normal_records.append({
            "voltage_v": round(float(voltage), 2),
            "current_a": round(float(current), 2),
            "power_kw": round(float(power_kw), 2),
            "battery_soc_pct": round(float(soc), 1),
            "charging_duration_minutes": round(float(duration), 1),
            "energy_consumed_kwh": round(float(energy_kwh), 2),
            "temperature_c": round(float(temp_c), 1),
            "is_anomaly": 0,
            "anomaly_type": "NORMAL",
        })

    anomaly_records = []
    anomaly_types = [
        "VOLTAGE_SAG",
        "OVERCURRENT_SPIKE",
        "CABLE_OVERHEATING",
        "SENSOR_STALL_GLITCH",
        "BMS_TAPER_VIOLATION",
    ]

    for _ in range(n_anomaly):
        atype = np.random.choice(anomaly_types)
        soc = np.random.uniform(20.0, 95.0)
        duration = np.random.uniform(10.0, 60.0)

        if atype == "VOLTAGE_SAG":
            # Grid drop: voltage drops to 280V while current surges to compensate
            voltage = np.random.uniform(250.0, 310.0)
            current = np.random.uniform(260.0, 340.0)
            power_kw = (voltage * current) / 1000.0
            temp_c = np.random.uniform(55.0, 68.0)
            energy_kwh = (power_kw * (duration / 60.0)) * 0.95

        elif atype == "OVERCURRENT_SPIKE":
            # Dangerous current spike
            voltage = np.random.uniform(390.0, 420.0)
            current = np.random.uniform(360.0, 480.0)
            power_kw = (voltage * current) / 1000.0
            temp_c = np.random.uniform(65.0, 80.0)
            energy_kwh = (power_kw * (duration / 60.0)) * 1.1

        elif atype == "CABLE_OVERHEATING":
            # Thermal runaway in dispenser liquid cooling
            voltage = np.random.uniform(380.0, 410.0)
            current = np.random.uniform(140.0, 200.0)
            power_kw = (voltage * current) / 1000.0
            temp_c = np.random.uniform(82.0, 98.0)  # Dangerously hot (>80°C)
            energy_kwh = (power_kw * (duration / 60.0)) * 0.9

        elif atype == "SENSOR_STALL_GLITCH":
            # Meter hardware failure: power is delivering but meter reads 0 kWh
            voltage = np.random.uniform(390.0, 410.0)
            current = np.random.uniform(120.0, 180.0)
            power_kw = 0.0  # Meter sensor frozen
            temp_c = np.random.uniform(35.0, 45.0)
            energy_kwh = 0.0  # Meter reads zero despite charging duration

        else:  # BMS_TAPER_VIOLATION
            # Vehicle at 97% SOC drawing maximum 150 kW (BMS failure)
            soc = np.random.uniform(93.0, 99.0)
            voltage = 425.0
            current = np.random.uniform(280.0, 350.0)
            power_kw = (voltage * current) / 1000.0
            temp_c = np.random.uniform(58.0, 72.0)
            energy_kwh = (power_kw * (duration / 60.0)) * 1.0

        anomaly_records.append({
            "voltage_v": round(float(voltage), 2),
            "current_a": round(float(current), 2),
            "power_kw": round(float(power_kw), 2),
            "battery_soc_pct": round(float(soc), 1),
            "charging_duration_minutes": round(float(duration), 1),
            "energy_consumed_kwh": round(float(energy_kwh), 2),
            "temperature_c": round(float(temp_c), 1),
            "is_anomaly": 1,
            "anomaly_type": atype,
        })

    all_records = normal_records + anomaly_records
    df = pd.DataFrame(all_records)
    # Shuffle so anomalies are distributed throughout
    df = df.sample(frac=1.0, random_state=seed).reset_index(drop=True)
    df.to_csv(output_path, index=False)
    print(f"Generated {len(df):,} telemetry observations ({n_anomaly} anomalies) saved to: {output_path}")
    return df


if __name__ == "__main__":
    generate_telemetry_dataset()

