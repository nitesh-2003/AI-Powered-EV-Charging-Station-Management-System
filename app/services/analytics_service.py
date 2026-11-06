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

        # Pre-aggregate station session counts and revenue in a single GROUP BY query (prevents N+1 query issue)
        session_aggregates = (
            db.query(
                ChargingPoint.station_id,
                func.count(ChargingSession.id).label("total_sessions"),
                func.coalesce(func.sum(ChargingSession.total_cost), Decimal("0.00")).label("total_revenue"),
            )
            .join(ChargingSession, ChargingSession.charging_point_id == ChargingPoint.id)
            .filter(ChargingSession.status == "COMPLETED")
            .group_by(ChargingPoint.station_id)
            .all()
        )
        station_session_map = {row[0]: (row[1], row[2]) for row in session_aggregates}

        # Station-wise breakdown
        stations = db.query(ChargingStation).all()
        station_breakdown: List[StationAnalytics] = []
        for st in stations:
            points = st.charging_points
            avail = sum(1 for p in points if p.status == "AVAILABLE")
            occ = sum(1 for p in points if p.status == "OCCUPIED")

            st_sessions, st_rev = station_session_map.get(st.id, (0, Decimal("0.00")))

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

        # 7-day revenue & session trend aggregated in a single query
        today = datetime.now(timezone.utc).date()
        seven_days_ago = datetime.combine(today - timedelta(days=6), datetime.min.time(), tzinfo=timezone.utc)

        daily_aggregates = (
            db.query(
                func.date(ChargingSession.created_at).label("day"),
                func.coalesce(func.sum(ChargingSession.total_cost), Decimal("0.00")).label("rev"),
                func.coalesce(func.sum(ChargingSession.total_energy_kwh), Decimal("0.00")).label("energy"),
                func.count(ChargingSession.id).label("sessions"),
            )
            .filter(
                ChargingSession.created_at >= seven_days_ago,
                ChargingSession.status == "COMPLETED",
            )
            .group_by(func.date(ChargingSession.created_at))
            .all()
        )
        daily_map = {row[0]: (row[1], row[2], row[3]) for row in daily_aggregates}

        revenue_trend: List[Dict[str, Any]] = []
        for i in range(6, -1, -1):
            day = today - timedelta(days=i)
            # Match day string or date object
            stats = daily_map.get(day) or daily_map.get(str(day))
            if stats:
                d_rev, d_energy, d_count = stats
            else:
                d_rev, d_energy, d_count = Decimal("0.00"), Decimal("0.00"), 0

            revenue_trend.append(
                {
                    "date": day.strftime("%b %d"),
                    "revenue": float(d_rev),
                    "energy_kwh": float(d_energy),
                    "sessions": d_count,
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

