"""
NIM Sentinel Main Application Entry Point

FastAPI application with all routes and middleware.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from nim_sentinel.api import router as api_router
from nim_sentinel.core.config import get_settings
from nim_sentinel.core.logging import setup_logging
from nim_sentinel.db.client import close_mongo_connection, connect_to_mongo

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    # Startup
    logger.info("Starting NIM Sentinel API")
    await connect_to_mongo()
    logger.info("MongoDB connected")

    yield

    # Shutdown
    logger.info("Shutting down NIM Sentinel API")
    await close_mongo_connection()
    logger.info("MongoDB disconnected")


app = FastAPI(
    title="NIM Sentinel API",
    description="Enterprise Multi-Agent Knowledge & Operations Copilot",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router)


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "name": "NIM Sentinel API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/v1/health",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "nim_sentinel.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
        workers=settings.api_workers if not settings.api_reload else 1,
    )
