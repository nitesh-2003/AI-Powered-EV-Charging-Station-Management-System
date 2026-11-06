import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.api import api_router
from app.core.database import engine, Base, SessionLocal

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler initializing schema and demo data on local dev."""
    if "sqlite" in str(engine.url):
        logger.info("Initializing schema tables on local SQLite database...")
        Base.metadata.create_all(bind=engine)
        # Check if users exist; if empty, seed demo data automatically
        db = SessionLocal()
        try:
            from app.models.user import User
            if not db.query(User).first():
                logger.info("Seeding demonstration stations, dispensers, and users...")
                from scripts.seed_demo_data import seed
                seed()
        except Exception as e:
            logger.warning("Could not auto-seed demo data: %s", e)
        finally:
            db.close()
    yield


# Create FastAPI application instance
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Enterprise-grade REST API backend for managing EV charging plazas, real-time slots, telemetry, and AI services.",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Set up CORS middleware
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include API v1 router
app.include_router(api_router, prefix=settings.API_V1_STR)

# Mount frontend web application static files
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
if os.path.isdir(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
