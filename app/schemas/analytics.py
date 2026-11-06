from decimal import Decimal
from typing import List, Dict, Any
from pydantic import BaseModel


class StationAnalytics(BaseModel):
    station_id: str
    station_name: str
    total_points: int
    available_points: int
    occupied_points: int
    total_sessions: int
    revenue: Decimal


class DashboardMetrics(BaseModel):
    total_users: int
    total_stations: int
    total_points: int
    available_points: int
    occupied_points: int
    faulted_points: int
    total_bookings: int
    active_sessions: int
    completed_sessions: int
    total_energy_kwh: Decimal
    total_revenue: Decimal
    station_breakdown: List[StationAnalytics]
    revenue_trend: List[Dict[str, Any]]
