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

    # Start background calendar sync (if configured)
    from app.services.background_calendar_sync import start_background_sync
    from app.integrations.google_calendar import get_google_calendar_integration

    gcal = get_google_calendar_integration()
    if gcal.is_configured():
        await start_background_sync(interval_minutes=15)
        print("Background calendar sync initialized")
    else:
        print("Google Calendar not configured, skipping background sync")

    yield

    # Shutdown
    print("Shutting down DocAssist Practice Manager API...")

    # Stop background sync
    from app.services.background_calendar_sync import stop_background_sync
    await stop_background_sync()
    print("Background calendar sync stopped")


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
