"""
FastAPI main application for DocAssist Practice Manager.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_router
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    print("Starting DocAssist Practice Manager API...")

    # Initialize realtime service with WebSocket connection manager
    from app.api.v1.websocket import get_connection_manager
    from app.services.realtime import get_realtime_service

    realtime_service = get_realtime_service()
    connection_manager = get_connection_manager()
    realtime_service.set_connection_manager(connection_manager)

    print("Real-time WebSocket service initialized")

    # Initialize report scheduler
    from app.services.report_scheduler import start_scheduler

    await start_scheduler()
    print("Report scheduler initialized")

    yield

    # Shutdown
    print("Shutting down DocAssist Practice Manager API...")

    # Stop report scheduler
    from app.services.report_scheduler import stop_scheduler

    await stop_scheduler()
    print("Report scheduler stopped")


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="Premium appointment scheduling and practice management system for doctors",
    openapi_url=f"{settings.api_v1_prefix}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": settings.version,
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": settings.version,
    }
