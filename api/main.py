"""
FastAPI Backend for Specify System

Production-ready FastAPI application that exposes the entire Specify system
(Phases 1-4) via REST + WebSocket APIs.

This is the main entry point for the Specify web application backend.
"""

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

# Add the src directory to the path so we can import our modules
sys.path.append(str(Path(__file__).parent.parent / "src"))

from api.config import get_settings
from api.middleware.logging_middleware import LoggingMiddleware
from api.middleware.error_handler import CustomExceptionHandler
from api.services.session_manager import SessionManager
from api.routers import (
    analyzer,
    specification,
    refinement,
    dispatch,
    websocket,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("api.log")
    ]
)

logger = logging.getLogger(__name__)

# Global session manager
session_manager = SessionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    # Startup
    logger.info("Starting Specify API backend...")

    # Initialize session manager
    await session_manager.initialize()

    # Add session manager to app state
    app.state.session_manager = session_manager

    logger.info("Specify API backend started successfully")

    yield

    # Shutdown
    logger.info("Shutting down Specify API backend...")
    await session_manager.cleanup()
    logger.info("Specify API backend shut down")


# Create FastAPI application
def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Specify API",
        description="Production-ready REST + WebSocket API for the Specify system",
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add trusted host middleware
    if settings.allowed_hosts:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=settings.allowed_hosts
        )

    # Add custom middleware
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(CustomExceptionHandler)

    # Include routers
    app.include_router(analyzer.router, prefix="/api", tags=["analyzer"])
    app.include_router(specification.router, prefix="/api", tags=["specification"])
    app.include_router(refinement.router, prefix="/api", tags=["refinement"])
    app.include_router(dispatch.router, prefix="/api", tags=["dispatch"])
    app.include_router(websocket.router, prefix="/api", tags=["websocket"])

    # Global exception handlers
    @app.exception_handler(HTTPException)
    async def custom_http_exception_handler(request: Request, exc: HTTPException):
        logger.error(f"HTTP exception: {exc.status_code} - {exc.detail}")
        return await http_exception_handler(request, exc)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.error(f"Validation error: {exc.errors()}")
        return await request_validation_exception_handler(request, exc)

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.exception("Unexpected error occurred")
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "type": "internal_error",
                "error_id": str(id(exc))
            }
        )

    return app


# Create the application instance
app = create_app()


# Health check endpoints
@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "specify-api",
        "version": "1.0.0"
    }


@app.get("/api/version")
async def version_info():
    """Get version and system information."""
    from src.analyzer import __version__ as analyzer_version
    from src.engine import __version__ as engine_version
    from src.refinement import __version__ as refinement_version
    from src.dispatcher import __version__ as dispatcher_version

    return {
        "api_version": "1.0.0",
        "components": {
            "analyzer": analyzer_version,
            "engine": engine_version,
            "refinement": refinement_version,
            "dispatcher": dispatcher_version
        },
        "description": "Specify System API - Multi-phase prompt specification and execution"
    }


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Specify API Backend",
        "docs_url": "/api/docs",
        "health_url": "/api/health",
        "version_url": "/api/version"
    }


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "api.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info" if not settings.debug else "debug"
    )