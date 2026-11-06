import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_active_user, require_admin
from app.models.user import User
from app.schemas.charging_session import SessionStart, SessionStop, SessionResponse
from app.services.session_service import SessionService

router = APIRouter()


@router.post(
    "/start",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start an EV charging session",
)
def start_charging_session(
    session_in: SessionStart,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Initiates power delivery session, marks dispenser OCCUPIED, records initial meter."""
    return SessionService.start_session(db, user=current_user, session_in=session_in)


@router.post(
    "/{session_id}/stop",
    response_model=SessionResponse,
    summary="Stop an active charging session and generate invoice",
)
def stop_charging_session(
    session_id: uuid.UUID,
    stop_in: SessionStop,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Stops charging session, computes kWh delivered, calculates tariff cost, marks point AVAILABLE."""
    return SessionService.stop_session(db, session_id=session_id, user=current_user, stop_in=stop_in)


@router.get(
    "/my",
    response_model=List[SessionResponse],
    summary="Get authenticated customer's charging session history",
)
def get_my_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Lists all charging sessions and invoices for the logged-in customer."""
    return SessionService.get_user_sessions(db, user_id=current_user.id)


@router.get(
    "",
    response_model=List[SessionResponse],
    summary="List all network charging sessions (Admin Only)",
)
@router.get(
    "/",
    response_model=List[SessionResponse],
    include_in_schema=False,
)
def list_all_sessions(
    status: Optional[str] = Query(None, description="Filter: 'IN_PROGRESS', 'COMPLETED', 'STOPPED'"),
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    """Admin-only monitoring of all charging sessions across the network."""
    return SessionService.get_all(db, status=status)


@router.get(
    "/{session_id}",
    response_model=SessionResponse,
    summary="Get single charging session details & invoice",
)
def get_session_details(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Retrieve session telemetry, energy delivered, and invoice details."""
    session = SessionService.get_by_id(db, session_id=session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Charging session not found",
        )
    if current_user.role != "ADMIN" and session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to session details",
        )
    return session

