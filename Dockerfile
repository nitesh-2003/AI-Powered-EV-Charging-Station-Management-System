# =============================================================================
# Dockerfile - AI-Powered EV Charging Station Management System
# Multi-stage build for a secure, optimized production image.
# =============================================================================

# ---------------------------------------------------------------------------
# Stage 1: Builder – install Python dependencies into a virtual environment
# ---------------------------------------------------------------------------
FROM python:3.13-slim AS builder

# System packages required to compile psycopg2 and other C-extension wheels
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Install Python dependencies into a dedicated venv so we can copy it cleanly
RUN python -m venv /build/venv
ENV PATH="/build/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ---------------------------------------------------------------------------
# Stage 2: Runtime – lean image with only what is needed to run the app
# ---------------------------------------------------------------------------
FROM python:3.13-slim AS runtime

# Runtime dependency: libpq is needed by psycopg2 at runtime
RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq5 curl && \
    rm -rf /var/lib/apt/lists/*

# Create a non-root user for security
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --create-home appuser

WORKDIR /home/appuser/app

# Copy the virtual environment from the builder stage
COPY --from=builder /build/venv /home/appuser/venv
ENV PATH="/home/appuser/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Copy application source code and assets
COPY app/          ./app/
COPY frontend/     ./frontend/
COPY docs/         ./docs/
COPY ml_models/    ./ml_models/
COPY ml_data/      ./ml_data/
COPY migrations/   ./migrations/
COPY alembic.ini   ./alembic.ini

# Ensure the non-root user owns the application files
RUN chown -R appuser:appuser /home/appuser

USER appuser

EXPOSE 8000

# Healthcheck: verify the API responds within 5 s, check every 30 s
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl --fail http://localhost:8000/health || exit 1

# Start the ASGI server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
