from fastapi import APIRouter
from app.api.v1.endpoints import (
    health,
    auth,
    stations,
    charging_points,
    bookings,
    sessions,
    analytics,
)

api_router = APIRouter()

# Register endpoint routers
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication & Users"])
api_router.include_router(stations.router, prefix="/stations", tags=["Charging Stations"])
api_router.include_router(charging_points.router, prefix="/points", tags=["Charging Points (EVSE)"])
api_router.include_router(bookings.router, prefix="/bookings", tags=["Bookings & Reservations"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["Charging Sessions & Billing"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Operational Analytics"])
