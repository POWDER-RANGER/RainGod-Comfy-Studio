# ============================================================================
# RAINGOD Backend Dockerfile
# Production-grade multi-stage build
# ============================================================================

# ============================================================================
# Stage 1: Base Image
# ============================================================================
FROM python:3.10-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ============================================================================
# Stage 2: Dependencies
# ============================================================================
FROM base as dependencies

# Create app directory
WORKDIR /app

# Copy requirements
COPY backend/requirements.txt /app/backend/requirements.txt

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r backend/requirements.txt

# ============================================================================
# Stage 3: Production
# ============================================================================
FROM base as production

# Create app user (non-root)
RUN useradd -m -u 1000 raingod && \
    mkdir -p /app /app/outputs /app/logs /app/cache && \
    chown -R raingod:raingod /app

# Set working directory
WORKDIR /app

# Copy Python packages from dependencies stage
COPY --from=dependencies /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=dependencies /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=raingod:raingod backend/ /app/backend/
COPY --chown=raingod:raingod workflows/ /app/workflows/

# Create necessary directories
RUN mkdir -p /app/outputs /app/logs /app/cache /app/temp

# Switch to non-root user
USER raingod

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["uvicorn", "backend.rain_backend:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

# ============================================================================
# Stage 4: Development (Optional)
# ============================================================================
FROM production as development

# Switch back to root for installations
USER root

# Install development tools
RUN pip install \
    pytest \
    pytest-asyncio \
    pytest-cov \
    black \
    flake8 \
    mypy \
    ipython

# Switch back to app user
USER raingod

# Override command for development (with reload)
CMD ["uvicorn", "backend.rain_backend:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ============================================================================
# Build Arguments and Labels
# ============================================================================

ARG BUILD_DATE
ARG VCS_REF
ARG VERSION

LABEL org.label-schema.build-date=$BUILD_DATE \
      org.label-schema.name="RAINGOD Backend" \
      org.label-schema.description="Visual Generation Pipeline for AI Music Production" \
      org.label-schema.version=$VERSION \
      org.label-schema.vcs-ref=$VCS_REF \
      org.label-schema.vcs-url="https://github.com/POWDER-RANGER/RAINGOD-ComfyUI-Integration" \
      org.label-schema.schema-version="1.0" \
      maintainer="Curtis Charles Farrar <ORCID: 0009-0008-9273-2458>"
