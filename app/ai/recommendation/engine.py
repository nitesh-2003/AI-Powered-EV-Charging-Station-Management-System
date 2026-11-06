import math
import uuid
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session

from app.models.station import ChargingStation
from app.models.charging_point import ChargingPoint
from app.schemas.recommendation import (
    RecommendationRequest,
    RecommendationResponse,
    ScoredStationRecommendation,
)


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Computes great-circle distance between two GPS coordinates using the Haversine formula.
    Returns distance in kilometers.
    """
    radius = 6371.0  # Earth radius in kilometers

    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(radius * c, 2)


class StationRecommendationEngine:
    """
    Multi-criteria intelligent ranking engine for EV charging stations.
    Balances distance, real-time dispenser availability, charging speed,
    and electricity tariff rates with adaptive weighting based on battery SOC.
    """

    @staticmethod
    def recommend(
        db: Session,
        criteria: RecommendationRequest,
    ) -> RecommendationResponse:
        # Retrieve all active stations with their charging points
        stations = (
            db.query(ChargingStation)
            .filter(ChargingStation.status == "ACTIVE")
            .all()
        )

        # Dynamic weight adjustment based on battery SOC urgency
        is_critical_battery = criteria.battery_percentage < 20.0
        soc_alert = None

        if is_critical_battery:
            soc_alert = f"CRITICAL BATTERY ({criteria.battery_percentage:.1f}%): Prioritizing proximity and fast charging."
            w_distance = 0.45
            w_avail = 0.30
            w_power = 0.20
            w_price = 0.05
        else:
            w_avail = 0.35
            w_distance = 0.30
            w_power = 0.20
            w_price = 0.15

        def evaluate_stations(candidate_stations, max_dist_limit):
            candidates = []
            for st in candidate_stations:
                distance = haversine_distance_km(
                    criteria.user_latitude,
                    criteria.user_longitude,
                    st.latitude,
                    st.longitude,
                )
                if distance > max_dist_limit:
                    continue

                points = st.charging_points
                if not points:
                    continue

                # 2. Hardware compatibility filtering
                connectors = set(p.connector_type for p in points)
                if criteria.connector_type:
                    req_conn = criteria.connector_type.upper().strip()
                    if req_conn not in connectors:
                        continue
                    matching_points = [p for p in points if p.connector_type == req_conn]
                else:
                    matching_points = points

                if criteria.min_power_kw:
                    matching_points = [p for p in matching_points if p.power_kw >= criteria.min_power_kw]
                    if not matching_points:
                        continue

                # 3. Metric extraction
                total_pts = len(matching_points)
                avail_pts = sum(1 for p in matching_points if p.status == "AVAILABLE")
                max_power = max(p.power_kw for p in matching_points)
                min_price = min(float(p.price_per_kwh) for p in matching_points)

                # 4. Multi-factor component scoring (each normalized to 0 - 100)
                effective_radius = max(max_dist_limit, 50.0)
                dist_score = max(0.0, (1.0 - (distance / effective_radius))) * 100.0

                if avail_pts > 0:
                    avail_score = (avail_pts / total_pts) * 100.0
                else:
                    avail_score = 5.0

                power_score = min(100.0, (max_power / 150.0) * 100.0)
                price_norm = max(0.0, 1.0 - max(0.0, (min_price - 10.0) / 25.0))
                price_score = price_norm * 100.0

                final_score = (
                    (w_distance * dist_score)
                    + (w_avail * avail_score)
                    + (w_power * power_score)
                    + (w_price * price_score)
                )
                final_score = round(max(0.0, min(100.0, final_score)), 1)

                if is_critical_battery:
                    reason = f"Fastest reach ({distance:.1f} km away) with {max_power:.0f} kW power output."
                elif avail_pts > 0:
                    reason = f"{avail_pts} of {total_pts} bays open, {distance:.1f} km away with up to {max_power:.0f} kW."
                else:
                    reason = f"All bays currently occupied; {distance:.1f} km away with {max_power:.0f} kW capability."

                candidates.append(
                    ScoredStationRecommendation(
                        rank=0,
                        station_id=st.id,
                        station_name=st.name,
                        address=st.address,
                        latitude=st.latitude,
                        longitude=st.longitude,
                        distance_km=distance,
                        available_points=avail_pts,
                        total_points=total_pts,
                        max_power_kw=max_power,
                        min_price_per_kwh=min_price,
                        compatible_connectors=sorted(list(connectors)),
                        recommendation_score=final_score,
                        score_breakdown={
                            "distance_score": round(dist_score, 1),
                            "availability_score": round(avail_score, 1),
                            "power_score": round(power_score, 1),
                            "price_score": round(price_score, 1),
                        },
                        recommendation_reason=reason,
                    )
                )
            return candidates

        search_radius = criteria.max_distance_km or 2500.0
        scored_candidates = evaluate_stations(stations, search_radius)

        # Resilient fallback: if distance limit filtered everything out, expand radius to all active stations
        if not scored_candidates and stations:
            scored_candidates = evaluate_stations(stations, 20000.0)

        # 5. Sort by descending recommendation score
        scored_candidates.sort(key=lambda s: s.recommendation_score, reverse=True)

        # Assign final ranks
        for idx, rec in enumerate(scored_candidates):
            rec.rank = idx + 1

        return RecommendationResponse(
            total_found=len(scored_candidates),
            user_location={"latitude": criteria.user_latitude, "longitude": criteria.user_longitude},
            battery_soc_alert=soc_alert,
            recommendations=scored_candidates,
        )

