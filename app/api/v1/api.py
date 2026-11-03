from fastapi import APIRouter
from app.api.v1.endpoints import health, auth, stations, charging_points

api_router = APIRouter()

# Register endpoint routers
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication & Users"])
api_router.include_router(stations.router, prefix="/stations", tags=["Charging Stations"])
api_router.include_router(charging_points.router, prefix="/points", tags=["Charging Points (EVSE)"])
