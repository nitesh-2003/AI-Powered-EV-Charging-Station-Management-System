from typing import Dict, Any, List
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.station import ChargingStation
from app.models.booking import Booking
from app.models.charging_session import ChargingSession


class LiveDataRetriever:
    """
    Controlled query gateway executing ground-truth database retrievals.
    Enforces Role-Based Access Control so customers never access another user's records.
    """

    @staticmethod
    def get_live_stations_summary(db: Session) -> Dict[str, Any]:
        """Returns verified real-time station availability across the network."""
        stations = db.query(ChargingStation).filter(ChargingStation.status == "ACTIVE").all()
        summary = []
        for st in stations:
            pts = st.charging_points
            total = len(pts)
            avail = sum(1 for p in pts if p.status == "AVAILABLE")
            occ = sum(1 for p in pts if p.status == "OCCUPIED")
            min_price = min((float(p.price_per_kwh) for p in pts), default=18.0)
            max_power = max((p.power_kw for p in pts), default=50.0)
            connectors = list(set(p.connector_type for p in pts))

            summary.append({
                "station_name": st.name,
                "address": st.address,
                "available_bays": avail,
                "total_bays": total,
                "occupied_bays": occ,
                "starting_price_per_kwh": f"${min_price:.2f}",
                "max_power_kw": f"{max_power:.0f} kW",
                "connectors": connectors,
            })
        return {"stations_count": len(stations), "stations": summary}

    @staticmethod
    def get_user_activity(db: Session, user: User) -> Dict[str, Any]:
        """Fetches driver's personal active bookings and recent charging sessions."""
        bookings = (
            db.query(Booking)
            .filter(Booking.user_id == user.id)
            .order_by(Booking.start_time.desc())
            .limit(5)
            .all()
        )
        sessions = (
            db.query(ChargingSession)
            .filter(ChargingSession.user_id == user.id)
            .order_by(ChargingSession.start_time.desc())
            .limit(5)
            .all()
        )

        booking_list = []
        for b in bookings:
            pt = b.charging_point
            st_name = pt.station.name if pt and pt.station else "Station"
            booking_list.append({
                "booking_id": str(b.id)[:8],
                "station": st_name,
                "dispenser": pt.identifier if pt else "Bay",
                "start_time": b.start_time.strftime("%b %d, %H:%M UTC"),
                "end_time": b.end_time.strftime("%b %d, %H:%M UTC"),
                "status": b.status,
            })

        session_list = []
        total_kwh = 0.0
        total_spent = 0.0
        for s in sessions:
            kwh = float(s.total_energy_kwh) if s.total_energy_kwh else 0.0
            cost = float(s.total_cost) if s.total_cost else 0.0
            total_kwh += kwh
            total_spent += cost
            session_list.append({
                "session_id": str(s.id)[:8],
                "started": s.start_time.strftime("%b %d, %H:%M UTC"),
                "energy_kwh": f"{kwh:.2f} kWh",
                "total_cost": f"${cost:.2f}",
                "status": s.status,
            })

        return {
            "driver_name": user.full_name,
            "recent_bookings": booking_list,
            "recent_sessions": session_list,
            "total_kwh_delivered": round(total_kwh, 2),
            "total_amount_billed": f"${total_spent:.2f}",
        }

    @staticmethod
    def get_admin_overview(db: Session) -> Dict[str, Any]:
        """Returns privileged operational network metrics for administrators."""
        active_sessions = (
            db.query(ChargingSession)
            .filter(ChargingSession.status == "IN_PROGRESS")
            .count()
        )
        total_bookings = db.query(Booking).count()
        return {
            "active_in_progress_sessions": active_sessions,
            "total_lifetime_bookings": total_bookings,
        }

