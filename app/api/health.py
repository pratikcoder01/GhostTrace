from datetime import datetime, timezone
from fastapi import APIRouter
from backend.app.config import settings
from backend.app.blockchain.storage import global_chain
from backend.app.blockchain.providers.provider_manager import provider_manager
from backend.app.services.event_pipeline import event_pipeline

from backend.app.mongodb import ping_mongodb

router = APIRouter(tags=["Health"])

@router.get("/health")
def get_health():
    """
    Returns system status, active database connectivity, TraceChain block height,
    service versions, and live ingestion provider health.
    """
    is_valid, msg, _ = global_chain.verify_chain()
    provider_status = provider_manager.get_status()
    mongo_health = ping_mongodb()

    overall_status = "healthy"
    if not mongo_health.get("connected"):
        overall_status = "degraded"

    return {
        "status": overall_status,
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tracechain": {
            "block_height": len(global_chain.chain),
            "integrity_valid": is_valid,
            "status": msg
        },
        "database": {
            "type": "mongodb",
            "status": mongo_health.get("status"),
            "connected": mongo_health.get("connected"),
            "database": mongo_health.get("database"),
            "latency_ms": mongo_health.get("latency_ms"),
            "is_mock": mongo_health.get("is_mock"),
            "endpoint": mongo_health.get("masked_uri")
        },
        "live_ingestion": {
            "provider": provider_status.provider_name,
            "connected": provider_status.connected,
            "connection_state": provider_status.connection_state,
            "last_processed_block": provider_status.last_processed_block,
            "queue_size": event_pipeline.get_queue_size(),
            "is_simulated": provider_status.is_simulated
        }
    }
