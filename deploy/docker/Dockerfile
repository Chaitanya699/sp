# NIM Sentinel Multi-stage Dockerfile
# Build: docker build -t nim-sentinel -f deploy/docker/Dockerfile .
# Run: docker run -p 8000:8000 --env-file .env nim-sentinel

# =============================================================================
# Base stage - common dependencies
# =============================================================================
FROM python:3.11-slim AS base

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set working directory
WORKDIR /app

# Install uv for fast dependency management
RUN pip install --no-cache-dir uv

# Copy dependency files
COPY pyproject.toml uv.lock* ./

# =============================================================================
# Development stage - with dev dependencies
# =============================================================================
FROM base AS development

# Install all dependencies including dev
RUN uv sync --frozen --all-extras

# Copy source code
COPY src/ ./src/
COPY configs/ ./configs/
COPY scripts/ ./scripts/
COPY evals/ ./evals/
COPY tests/ ./tests/

# Create logs directory
RUN mkdir -p logs && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/healthz || exit 1

# Default command
CMD ["uvicorn", "nim_sentinel.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# =============================================================================
# Production stage - minimal image
# =============================================================================
FROM base AS production

# Install only production dependencies
RUN uv sync --frozen --no-dev

# Copy source code
COPY src/ ./src/
COPY configs/ ./configs/
COPY scripts/ ./scripts/

# Create logs directory
RUN mkdir -p logs && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/healthz || exit 1

# Default command
CMD ["uvicorn", "nim_sentinel.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

# =============================================================================
# UI stage - Streamlit
# =============================================================================
FROM base AS ui

# Install UI dependencies
RUN uv sync --frozen --extra ui

# Copy UI source
COPY ui/ ./ui/
COPY src/ ./src/
COPY configs/ ./configs/

# Create logs directory
RUN mkdir -p logs && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Default command
CMD ["streamlit", "run", "ui/app.py", "--server.port=8501", "--server.address=0.0.0.0"]

# =============================================================================
# Test stage - for running tests in CI
# =============================================================================
FROM development AS test

# Install test dependencies
RUN uv sync --frozen --extra test

# Copy test files
COPY tests/ ./tests/
COPY evals/ ./evals/

# Run tests
CMD ["pytest", "tests/", "-v", "--tb=short"]