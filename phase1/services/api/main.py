"""
FastAPI application for REST and WebSocket APIs.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog

from ..config import get_settings
from ..persistence import init_database, get_database
from .routes import bars, ingest, parity, debug, clock, drawings, strategies, portfolio, alerts, versions, runs, packages, metrics, incidents, notes, reports
from .websocket import router as ws_router


logger = structlog.get_logger()


from ..ingestion.main import IngestionService
import os

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("application_startup")
    
    # Initialize database
    await init_database()
    logger.info("database_initialized")
    
    # Start Ingestion Service (Background)
    settings = get_settings()
    
    # Determine mode based on configured provider keys
    mode = "mock"
    csv_path = None
    provider_override = None

    if settings.apca_api_key_id:
        mode = "live"
        provider_override = "alpaca"
        logger.info("using_alpaca_live_data")
    elif settings.finnhub_api_key:
        mode = "live"
        provider_override = "finnhub"
        logger.info("using_finnhub_live_data")
    else:
        # Fallback to mock with sample CSV
        mode = "mock"
        csv_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "sample_ticks.csv")
        logger.info("using_mock_csv_data", path=csv_path)

    ingestion = IngestionService(mode=mode, symbols=["AAPL", "TSLA", "MSFT"], provider=provider_override) # Default symbols
    
    # Start ingestion
    try:
        await ingestion.start()

        # Expose ingestion on app state for status endpoints
        try:
            app.state.ingestion = ingestion
        except Exception:
            pass
        
        if mode == "mock" and csv_path and os.path.exists(csv_path):
            # Run replay in background task
            asyncio.create_task(ingestion.run_mock_replay(csv_path))
            
    except Exception as e:
        logger.error("ingestion_startup_failed", error=str(e))
    
    yield
    
    # Cleanup Ingestion
    await ingestion.stop()
    
    # Cleanup DB
    db = get_database()
    await db.close()
    logger.info("application_shutdown")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()
    
    app = FastAPI(
        title="Phase 1: Deterministic Bar Engine API",
        description="REST and WebSocket APIs for bar data",
        version="1.0.0",
        lifespan=lifespan,
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(bars.router, prefix="/api/v1/bars", tags=["bars"])
    app.include_router(ingest.router, prefix="/api/v1/ingest", tags=["ingest"])
    app.include_router(parity.router, prefix="/api/v1/parity", tags=["parity"])
    app.include_router(debug.router, prefix="/api/v1/debug", tags=["debug"])
    app.include_router(clock.router, prefix="/api/v1/clock", tags=["clock"])
    app.include_router(drawings.router, prefix="/api/v1/drawings", tags=["drawings"])
    app.include_router(strategies.router, prefix="/api/v1/strategies", tags=["strategies"])
    app.include_router(portfolio.router, prefix="/api/v1/portfolio", tags=["portfolio"])
    app.include_router(alerts.router, prefix="/api/v1/alerts", tags=["alerts"])
    app.include_router(versions.router, prefix="/api/v1", tags=["versions"])
    app.include_router(runs.router, prefix="/api/v1", tags=["runs"])
    app.include_router(packages.router, prefix="/api/v1", tags=["packages"])
    app.include_router(metrics.router, prefix="/api/v1", tags=["metrics"])
    app.include_router(incidents.router, prefix="/api/v1", tags=["incidents"])
    app.include_router(notes.router, prefix="/api/v1", tags=["notes"])
    app.include_router(reports.router, prefix="/api/v1", tags=["reports"])
    app.include_router(ws_router, prefix="/ws", tags=["websocket"])
    
    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error("unhandled_exception", error=str(exc), path=request.url.path)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "detail": str(exc)},
        )
    
    # Health check
    @app.get("/health")
    async def health_check():
        return {"status": "healthy"}
    
    # Root endpoint
    @app.get("/")
    async def root():
        return {
            "name": "Phase 1 Bar Engine API",
            "version": "1.0.0",
            "docs": "/docs",
        }
    
    return app


# Create default app instance
app = create_app()
