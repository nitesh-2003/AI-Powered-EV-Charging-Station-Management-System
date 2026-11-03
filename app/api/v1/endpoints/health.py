from fastapi import APIRouter, status
from app.core.config import settings

router = APIRouter()


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Health Check Endpoint",
    description="Returns the operational status, project name, and version of the backend service.",
)
def check_health():
    """
    Standard health check endpoint used by uptime monitors, load balancers,
    and frontend applications to verify service availability.
    """
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": "debug" if settings.DEBUG else "production",
    }
