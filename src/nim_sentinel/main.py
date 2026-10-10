"""
NIM Sentinel Main Application Entry Point

FastAPI application with all routes and middleware.
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from nim_sentinel.api import router as api_router
from nim_sentinel.core.config import get_settings
from nim_sentinel.core.logging import setup_logging
from nim_sentinel.db.client import close_mongo_connection, connect_to_mongo
from nim_sentinel.llm.model_registry import get_model_registry

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

settings = get_settings()


async def check_model_health() -> None:
    """Non-blocking health check for configured models at startup."""
    try:
        registry = get_model_registry()
        roles = [
            "supervisor_llm",
            "critic_llm",
            "generator_llm",
            "code_llm",
            "reasoning_llm",
            "embedding",
            "reranker",
        ]

        for role in roles:
            try:
                # Just verify the model can be instantiated (doesn't make API call)
                if role in ["embedding"]:
                    registry.get_embedding_model(role)
                elif role in ["reranker"]:
                    registry.get_rerank_model(role)
                else:
                    registry.get_chat_model(role)
                logger.info(f"Model health check OK: {role}")
            except Exception as e:
                # Non-blocking: log WARNING but don't fail startup
                logger.warning(f"Model health check failed for {role}: {e}")
    except Exception as e:
        logger.warning(f"Model health check skipped: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    # Startup
    logger.info("Starting NIM Sentinel API")
    await connect_to_mongo()
    logger.info("MongoDB connected")

    # Non-blocking model health checks
    await check_model_health()

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
