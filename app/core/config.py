import sys
import logging
from typing import List, Optional, Union
import json
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

_DEFAULT_SECRET = "insecure-dev-secret-key-change-this-for-production"


class Settings(BaseSettings):
    """
    Application Settings parsed from environment variables and .env file.
    Follows the 12-factor app design pattern.
    """
    PROJECT_NAME: str = "AI-Powered EV Charging Station Management System"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = True

    # Security & Authentication
    SECRET_KEY: str = _DEFAULT_SECRET
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # PostgreSQL Database Connection
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "ev_charging_db"
    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/ev_charging_db"

    # CORS Origins
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    ]

    # Generative AI (Optional)
    GEMINI_API_KEY: Optional[str] = None

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        """Ensures CORS origins can be read as a JSON list or comma-separated string."""
        if isinstance(v, str):
            if v.startswith("["):
                return json.loads(v)
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @model_validator(mode="after")
    def _validate_production_security(self) -> "Settings":
        """
        Production safety gate: prevents the application from starting in
        non-DEBUG mode with the default insecure secret key.
        """
        if not self.DEBUG and self.SECRET_KEY == _DEFAULT_SECRET:
            logger.critical(
                "FATAL: SECRET_KEY must be changed from the default value "
                "before running in production (DEBUG=False). Generate a "
                "secure key with: python -c \"import secrets; print(secrets.token_urlsafe(64))\""
            )
            sys.exit(1)
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


# Global singleton instance of settings
settings = Settings()

