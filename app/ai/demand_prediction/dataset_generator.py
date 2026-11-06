import os
import math
import numpy as np
import pandas as pd
from datetime import datetime, timedelta, timezone


def generate_historical_charging_dataset(
    output_path: str = "ml_data/historical_demand.csv",
    num_days: int = 120,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Generates a realistic, synthetic historical charging dataset modeling hourly
    charging events across 4 diverse charging plazas over 120 days.
    
    Reflects authentic real-world EV charging behaviors:
    - Commuter plazas: Twin peaks at 8-10 AM and 5-8 PM on weekdays.
    - Highway plazas: Heavy surge on Friday evenings, Saturday mornings, Sunday evenings.
    - Temperature effects: Extreme cold (<5C) or heat (>35C) increases energy draw.
    - Realistic variance: Poisson-distributed arrivals capped by station dispenser capacity.
    """
    np.random.seed(seed)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    stations = [
        {"id": "station-alpha-dt", "name": "Downtown Tech Corridor Hub", "type": "URBAN_COMMUTER", "capacity": 10, "base_kw": 50.0},
        {"id": "station-beta-hw", "name": "Interstate-95 Fast Plaza", "type": "HIGHWAY_CORRIDOR", "capacity": 12, "base_kw": 150.0},
        {"id": "station-gamma-sub", "name": "Westside Suburban Mall Hub", "type": "RETAIL_DESTINATION", "capacity": 8, "base_kw": 22.0},
        {"id": "station-delta-air", "name": "Metro Airport Long-Stay Plaza", "type": "FLEET_TRANSIT", "capacity": 14, "base_kw": 60.0},
    ]

    end_time = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    start_time = end_time - timedelta(days=num_days)

    records = []
    current_time = start_time

    while current_time < end_time:
        hour = current_time.hour
        day_of_week = current_time.weekday()  # 0=Monday, 6=Sunday
        is_weekend = 1 if day_of_week in [5, 6] else 0
        day_of_year = current_time.timetuple().tm_yday

        # Seasonal temperature cycle (10°C to 35°C variation)
        temp_c = 22.0 + 10.0 * math.sin(2 * math.pi * (day_of_year - 80) / 365) + 4.0 * math.sin(2 * math.pi * (hour - 9) / 24)
        temp_c += np.random.normal(0, 1.5)
        temp_c = round(temp_c, 1)

        # Temperature load factor (extreme heat or cold drains HVAC, increasing charge need)
        temp_factor = 1.0
        if temp_c < 8.0:
            temp_factor += (8.0 - temp_c) * 0.02
        elif temp_c > 32.0:
            temp_factor += (temp_c - 32.0) * 0.025

        for st in stations:
            st_type = st["type"]
            cap = st["capacity"]
            base_kw = st["base_kw"]

            # Hourly arrival intensity profile based on station classification
            if st_type == "URBAN_COMMUTER":
                if not is_weekend:
                    # Bimodal peaks at 8-10 AM and 5-8 PM
                    morning_peak = math.exp(-0.5 * ((hour - 9) / 1.5) ** 2)
                    evening_peak = math.exp(-0.5 * ((hour - 18) / 1.8) ** 2)
                    midday = 0.35 if 11 <= hour <= 15 else 0.1
                    profile = 0.85 * morning_peak + 0.95 * evening_peak + midday
                else:
                    # Weekend daytime moderate shopping traffic
                    profile = 0.35 * math.exp(-0.5 * ((hour - 14) / 3.0) ** 2)

            elif st_type == "HIGHWAY_CORRIDOR":
                if is_weekend or day_of_week == 4:  # Friday afternoon + Weekends
                    friday_surge = 0.9 if day_of_week == 4 and 16 <= hour <= 21 else 0.0
                    sat_surge = 0.85 if day_of_week == 5 and 9 <= hour <= 14 else 0.0
                    sun_surge = 0.95 if day_of_week == 6 and 15 <= hour <= 21 else 0.0
                    profile = max(0.2, friday_surge + sat_surge + sun_surge)
                else:
                    profile = 0.3 * math.exp(-0.5 * ((hour - 13) / 4.0) ** 2) + 0.1

            elif st_type == "RETAIL_DESTINATION":
                # Shopping mall peaks between 12 PM and 8 PM
                mall_curve = math.exp(-0.5 * ((hour - 15) / 3.0) ** 2) if 10 <= hour <= 21 else 0.05
                weekend_boost = 1.4 if is_weekend else 0.9
                profile = mall_curve * weekend_boost

            else:  # FLEET_TRANSIT
                # Fleet / Airport traffic has steady daytime flow and early morning departures
                profile = 0.45 + 0.35 * math.sin(math.pi * hour / 24)

            # Expected session count with Poisson noise
            expected_sessions = profile * (cap * 0.85) * temp_factor
            sessions_count = int(np.random.poisson(max(0.1, expected_sessions)))
            # Cannot exceed physical hardware dispensers
            sessions_count = min(sessions_count, cap)

            # Energy consumption per session (typically 20 kWh to 45 kWh depending on base kW)
            avg_kwh_per_session = min(65.0, 15.0 + (base_kw * 0.25) * np.random.uniform(0.85, 1.25))
            total_energy_kwh = round(sessions_count * avg_kwh_per_session, 2)

            records.append({
                "timestamp": current_time.isoformat(),
                "station_id": st["id"],
                "station_name": st["name"],
                "station_type": st_type,
                "total_dispensers": cap,
                "hour_of_day": hour,
                "day_of_week": day_of_week,
                "is_weekend": is_weekend,
                "temperature_c": temp_c,
                "charging_sessions": sessions_count,
                "total_energy_kwh": total_energy_kwh,
            })

        current_time += timedelta(hours=1)

    df = pd.DataFrame(records)
    df.to_csv(output_path, index=False)
    print(f"Generated {len(df):,} historical demand hourly records saved to: {output_path}")
    return df


if __name__ == "__main__":
    generate_historical_charging_dataset()

