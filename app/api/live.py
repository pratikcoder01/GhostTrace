from fastapi import APIRouter, HTTPException, status
from backend.app.schemas import LiveStatusResponse, SimulateEventRequest
from backend.app.blockchain.providers.provider_manager import provider_manager
from backend.app.services.event_pipeline import event_pipeline
from backend.app.services.live_osint_collector import live_osint_collector
from backend.app.ml.model_registry import model_registry
from backend.app.config import settings

router = APIRouter(prefix="/live", tags=["Real-Time Observability & Live Ingestion"])

@router.get("/status", response_model=LiveStatusResponse)
def get_live_status():
    """
    Returns real-time ingestion observability metrics:
    provider connection state, block heights, lag, queue size, OSINT source freshness,
    and active ML model thresholds.
    """
    provider_status = provider_manager.get_status()
    osint_status = live_osint_collector.get_sources_status()
    active_model = model_registry.load_active_model()
    model_version = active_model.get("version", "v1.0.0") if active_model else "unavailable"

    return LiveStatusResponse(
        status="active" if provider_status.connected else "standby",
        provider=provider_status,
        queue_size=event_pipeline.get_queue_size(),
        latest_analysis_time=event_pipeline.latest_analysis_time,
        osint_sources=osint_status,
        model_version=model_version,
        active_threshold=settings.ML_ACTIVE_THRESHOLD
    )

@router.post("/simulate-event", status_code=status.HTTP_201_CREATED)
async def simulate_event(req: SimulateEventRequest):
    """
    Injects a deterministic live blockchain event (native ETH or ERC-20 transfer, or reorg)
    into the ingestion pipeline for end-to-end testing, live UI verification, and demos.
    Clearly labeled as simulation.
    """
    from backend.app.blockchain.providers.simulator_provider import SimulatorProvider
    
    # If active provider is simulator, use its injection; otherwise construct an event
    from_addr = req.from_address or "0x71c7656ec7ab88b098defb751b7401b5f6d8976f"
    to_addr = req.to_address or "0x28c6c06298d514db089934071355e5743bf21d60"
    amount = req.amount or 2.5
    asset = req.asset or ("USDT" if req.tx_type == "erc20" else "ETH")
    is_removed = bool(req.is_removed)

    if isinstance(provider_manager.active_provider, SimulatorProvider):
        event = await provider_manager.active_provider.inject_event(
            from_address=from_addr,
            to_address=to_addr,
            amount=amount,
            asset=asset,
            is_removed=is_removed
        )
    else:
        # Construct and inject directly via pipeline
        from backend.app.blockchain.providers.simulator_provider import SimulatorProvider
        temp_sim = SimulatorProvider()
        event = await temp_sim.inject_event(
            from_address=from_addr,
            to_address=to_addr,
            amount=amount,
            asset=asset,
            is_removed=is_removed
        )
        await event_pipeline.process_blockchain_event(event)

    return {
        "status": "success",
        "message": "Simulated live event injected into pipeline.",
        "event_id": event.event_id,
        "tx_hash": event.tx_hash,
        "is_reorg": event.is_removed,
        "asset": event.asset,
        "amount": event.amount,
        "is_simulated": True
    }

@router.post("/osint/collect")
async def trigger_osint_collection():
    """Triggers an on-demand OSINT collection cycle across public feeds."""
    results = await live_osint_collector.collect_all()
    return {
        "status": "success",
        "collected_sources": results
    }
