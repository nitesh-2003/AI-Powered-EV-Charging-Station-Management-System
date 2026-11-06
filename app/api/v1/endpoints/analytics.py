from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import require_admin
from app.models.user import User
from app.schemas.analytics import DashboardMetrics
from app.services.analytics_service import AnalyticsService

router = APIRouter()


@router.get(
    "/dashboard",
    response_model=DashboardMetrics,
    summary="Get aggregated live operational analytics for Admin Dashboard",
)
def get_dashboard_metrics(
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    """Returns database-backed metrics for the admin command center and Chart.js visualizations."""
    return AnalyticsService.get_dashboard_metrics(db)
