from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token
from app.schemas.user import UserCreate, UserResponse, UserLogin
from app.schemas.token import Token
from app.services.user_service import UserService
from app.api.deps import get_current_active_user, require_admin
from app.models.user import User

router = APIRouter()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
def register(
    user_in: UserCreate,
    db: Session = Depends(get_db),
):
    """
    Registers a new user (Customer or Admin).
    Checks that the email address is not already registered.
    """
    existing_user = UserService.get_by_email(db, email=user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists.",
        )
    return UserService.create(db, user_in=user_in)


@router.post(
    "/login",
    response_model=Token,
    summary="User login with JSON credentials",
)
def login(
    login_data: UserLogin,
    db: Session = Depends(get_db),
):
    """Authenticates with JSON payload and returns signed JWT access token."""
    user = UserService.authenticate(
        db, email=login_data.email, password=login_data.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive.",
        )

    access_token = create_access_token(
        subject=user.id,
        role=user.role,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.post(
    "/login/access-token",
    response_model=Token,
    summary="OAuth2 compatible token login (for Swagger UI)",
)
def login_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """OAuth2 password form login used by Swagger UI Authorize button."""
    user = UserService.authenticate(
        db, email=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(
        subject=user.id,
        role=user.role,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current logged-in user profile",
)
def read_current_user(
    current_user: User = Depends(get_current_active_user),
):
    """Returns the authenticated user's profile information."""
    return current_user


@router.get(
    "/admin-test",
    summary="Protected route restricted strictly to Administrators",
)
def test_admin_access(
    current_admin: User = Depends(require_admin),
):
    """Demonstrates Role-Based Access Control (RBAC). Only accessible by ADMIN role."""
    return {
        "message": f"Hello Admin {current_admin.full_name}, you have privileged administrative access!",
        "role": current_admin.role,
    }
