import json
from fastapi import APIRouter
from backend.app.config import settings
from backend.app.adapters.elliptic import EllipticDatasetAdapter
from backend.app.adapters.ethereum import EthereumAdapter

router = APIRouter(tags=["Data Sources"])

@router.get("/data-sources")
def get_data_sources():
    """
    Returns discovery inventory of on-disk datasets, verified schemas, and provider adapter configurations.
    """
    elliptic = EllipticDatasetAdapter()
    eth = EthereumAdapter()

    sources = [
        {
            "id": "synthetic_ghost_attack",
            "name": "Operation Phantom Drain (Synthetic Scenario)",
            "network": "simulated",
            "format": "JSON",
            "available": settings.SYNTHETIC_ATTACK_FILE.exists(),
            "path": str(settings.SYNTHETIC_ATTACK_FILE),
            "description": "Deterministic multi-hop ghost attacks scenario with fan-out, fan-in, and planted threat intel indicators."
        },
        {
            "id": "cryptoscamdb",
            "name": "CryptoScamDB Blacklist Snapshot",
            "network": "cross_chain (ETH/BTC)",
            "format": "JSON",
            "available": settings.CRYPTOSCAMDB_FILE.exists(),
            "path": str(settings.CRYPTOSCAMDB_FILE),
            "description": "Verified open-source repository snapshot of reported scam wallets, phishing domains, and impersonation handles."
        },
        {
            "id": "elliptic",
            "name": "Elliptic Bitcoin AML Dataset",
            "network": "bitcoin",
            "format": "CSV (classes, edgelist, features)",
            "available": elliptic.is_available(),
            "path": str(settings.ELLIPTIC_DATA_DIR),
            "description": "203,769 Bitcoin transaction nodes across 49 chronological time steps with 165 graph features."
        },
        {
            "id": "pegasus_telemetry",
            "name": "Synthetic Pegasus Threat IOC Dataset",
            "network": "threat_intel",
            "format": "CSV",
            "available": settings.PEGASUS_CSV_FILE.exists(),
            "path": str(settings.PEGASUS_CSV_FILE),
            "description": "Host and network anomaly signatures linked to advanced surveillance intrusion indicators."
        },
        {
            "id": "ethereum_etherscan",
            "name": "Ethereum Live Read-Only Adapter (Etherscan)",
            "network": "ethereum",
            "format": "JSON-RPC / REST API",
            "available": eth.is_configured(),
            "description": "Optional bounded live transaction fetching. Operates in offline mode when API key is omitted."
        },
        {
            "id": "alchemy_websocket",
            "name": "Alchemy Ethereum WebSocket Live Stream",
            "network": "ethereum",
            "format": "WebSocket JSON-RPC (newHeads & logs)",
            "available": bool(settings.ALCHEMY_API_KEY and settings.ALCHEMY_API_KEY.strip()),
            "description": "Real-time streaming ingestion for new block headers and ERC-20 Transfer logs with reorg detection."
        },
        {
            "id": "live_osint_feeds",
            "name": "Configurable Live Public OSINT Collectors",
            "network": "multi_chain",
            "format": "REST API Feeds with SHA-256 Content Hashing",
            "available": True,
            "description": "Live collectors for CryptoScamDB, PhishFort, and URLhaus with bounded backoff and caching."
        }
    ]

    return {
        "status": "success",
        "total_sources": len(sources),
        "data_sources": sources
    }
