import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from backend.app.config import settings
from backend.app.database import init_db
from backend.app.blockchain.storage import TraceChainStorage
from backend.app.services.osint_service import osint_service
from backend.app.ml.model_registry import model_registry
from backend.app.blockchain.providers.provider_manager import provider_manager
from backend.app.services.event_pipeline import event_pipeline
from backend.app.services.live_osint_collector import live_osint_collector

from backend.app.api import health, cases, chain, data_sources, ml, live, ws

from backend.app.mongodb import connect_mongodb, close_mongodb

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup tasks
    logger.info("Initializing GhostTrace MongoDB connection and indexes...")
    try:
        connect_mongodb()
        init_db()
    except Exception as e:
        logger.error(f"MongoDB connection notice during startup: {e}. Running in degraded mode until connectivity is restored.")

    logger.info("Initializing TraceChain audit ledger...")
    TraceChainStorage.load_or_init_chain()

    logger.info("Warming up OSINT threat intelligence index...")
    try:
        osint_service.initialize()
    except Exception as e:
        logger.warning(f"OSINT warm-up notice: {e}")

    logger.info("Checking ML Model Registry...")
    active_model = model_registry.load_active_model()
    if active_model:
        logger.info(f"Loaded active ML model: {active_model['algorithm']} ({active_model['version']})")
    else:
        logger.info("No active model found in registry.")

    # Start Real-Time Ingestion & Event Pipeline
    logger.info("Starting asynchronous Event Pipeline...")
    await event_pipeline.start()

    logger.info("Starting Live Blockchain Provider Manager...")
    await provider_manager.start()
    p_status = provider_manager.get_status()
    mode_str = "SIMULATED" if p_status.is_simulated else "LIVE"
    logger.info(f"ACTIVE PROVIDER: {p_status.provider_name} | MODE: {mode_str}")

    logger.info("Starting Live OSINT Collector service...")
    await live_osint_collector.start_scheduled_collector()

    yield
    # Shutdown tasks
    logger.info("GhostTrace backend shutting down gracefully...")
    await live_osint_collector.stop()
    await provider_manager.stop()
    await event_pipeline.stop()
    close_mongodb()
    logger.info("All background tasks and database connections terminated safely.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "GhostTrace Forensic Intelligence Backend. "
        "Provides real-time blockchain ingestion, WebSocket event dispatch, "
        "transaction graph forensics, temporal burst analysis, "
        "OSINT correlation, machine learning illicit transaction classification, "
        "and custom cryptographic TraceChain audit logging."
    ),
    lifespan=lifespan
)

# CORS Middleware (allows frontend dashboard to query without cross-origin blocks)
cors_origins_env = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000")
cors_origins = [o.strip() for o in cors_origins_env.split(",") if o.strip()]
allow_all = "*" in cors_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=not allow_all,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers under /api and root health
app.include_router(health.router)
app.include_router(health.router, prefix=settings.API_V1_STR)
app.include_router(data_sources.router, prefix=settings.API_V1_STR)
app.include_router(cases.router, prefix=settings.API_V1_STR)
app.include_router(chain.router, prefix=settings.API_V1_STR)
app.include_router(ml.router, prefix=settings.API_V1_STR)
app.include_router(live.router, prefix=settings.API_V1_STR)

# Include WebSocket router at root (/ws/live) and under /api (/api/ws/live)
app.include_router(ws.router)
app.include_router(ws.router, prefix=settings.API_V1_STR)

@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")
