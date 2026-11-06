from decimal import Decimal
from typing import List, Dict, Any
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.user import User
from app.models.station import ChargingStation
from app.models.charging_point import ChargingPoint
from app.models.booking import Booking
from app.models.charging_session import ChargingSession
from app.schemas.analytics import DashboardMetrics, StationAnalytics


class AnalyticsService:
    """Service layer computing database-backed analytics and aggregations for admin dashboard."""

    @staticmethod
    def get_dashboard_metrics(db: Session) -> DashboardMetrics:
        total_users = db.query(func.count(User.id)).scalar() or 0
        total_stations = db.query(func.count(ChargingStation.id)).scalar() or 0
        total_points = db.query(func.count(ChargingPoint.id)).scalar() or 0

        available_points = (
            db.query(func.count(ChargingPoint.id))
            .filter(ChargingPoint.status == "AVAILABLE")
            .scalar()
            or 0
        )
        occupied_points = (
            db.query(func.count(ChargingPoint.id))
            .filter(ChargingPoint.status == "OCCUPIED")
            .scalar()
            or 0
        )
        faulted_points = (
            db.query(func.count(ChargingPoint.id))
            .filter(ChargingPoint.status == "FAULTED")
            .scalar()
            or 0
        )

        total_bookings = db.query(func.count(Booking.id)).scalar() or 0
        active_sessions = (
            db.query(func.count(ChargingSession.id))
            .filter(ChargingSession.status == "IN_PROGRESS")
            .scalar()
            or 0
        )
        completed_sessions = (
            db.query(func.count(ChargingSession.id))
            .filter(ChargingSession.status == "COMPLETED")
            .scalar()
            or 0
        )

        total_energy_kwh = (
            db.query(func.coalesce(func.sum(ChargingSession.total_energy_kwh), Decimal("0.00")))
            .filter(ChargingSession.status == "COMPLETED")
            .scalar()
        )
        total_revenue = (
            db.query(func.coalesce(func.sum(ChargingSession.total_cost), Decimal("0.00")))
            .filter(ChargingSession.status == "COMPLETED")
            .scalar()
        )

        # Station-wise breakdown
        stations = db.query(ChargingStation).all()
        station_breakdown: List[StationAnalytics] = []
        for st in stations:
            points = st.charging_points
            avail = sum(1 for p in points if p.status == "AVAILABLE")
            occ = sum(1 for p in points if p.status == "OCCUPIED")
            point_ids = [p.id for p in points]

            if point_ids:
                st_sessions = (
                    db.query(func.count(ChargingSession.id))
                    .filter(ChargingSession.charging_point_id.in_(point_ids))
                    .scalar()
                    or 0
                )
                st_rev = (
                    db.query(func.coalesce(func.sum(ChargingSession.total_cost), Decimal("0.00")))
                    .filter(
                        ChargingSession.charging_point_id.in_(point_ids),
                        ChargingSession.status == "COMPLETED",
                    )
                    .scalar()
                )
            else:
                st_sessions = 0
                st_rev = Decimal("0.00")

            station_breakdown.append(
                StationAnalytics(
                    station_id=str(st.id),
                    station_name=st.name,
                    total_points=len(points),
                    available_points=avail,
                    occupied_points=occ,
                    total_sessions=st_sessions,
                    revenue=Decimal(str(st_rev)),
                )
            )

        # 7-day revenue & session trend
        revenue_trend: List[Dict[str, Any]] = []
        today = datetime.now(timezone.utc).date()
        for i in range(6, -1, -1):
            day = today - timedelta(days=i)
            day_start = datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc)
            day_end = datetime.combine(day, datetime.max.time(), tzinfo=timezone.utc)

            day_rev = (
                db.query(func.coalesce(func.sum(ChargingSession.total_cost), Decimal("0.00")))
                .filter(
                    ChargingSession.status == "COMPLETED",
                    ChargingSession.created_at >= day_start,
                    ChargingSession.created_at <= day_end,
                )
                .scalar()
            )
            day_energy = (
                db.query(func.coalesce(func.sum(ChargingSession.total_energy_kwh), Decimal("0.00")))
                .filter(
                    ChargingSession.status == "COMPLETED",
                    ChargingSession.created_at >= day_start,
                    ChargingSession.created_at <= day_end,
                )
                .scalar()
            )
            day_count = (
                db.query(func.count(ChargingSession.id))
                .filter(
                    ChargingSession.created_at >= day_start,
                    ChargingSession.created_at <= day_end,
                )
                .scalar()
                or 0
            )

            revenue_trend.append(
                {
                    "date": day.strftime("%b %d"),
                    "revenue": float(day_rev),
                    "energy_kwh": float(day_energy),
                    "sessions": day_count,
                }
            )

        return DashboardMetrics(
            total_users=total_users,
            total_stations=total_stations,
            total_points=total_points,
            available_points=available_points,
            occupied_points=occupied_points,
            faulted_points=faulted_points,
            total_bookings=total_bookings,
            active_sessions=active_sessions,
            completed_sessions=completed_sessions,
            total_energy_kwh=Decimal(str(total_energy_kwh)),
            total_revenue=Decimal(str(total_revenue)),
            station_breakdown=station_breakdown,
            revenue_trend=revenue_trend,
        )
