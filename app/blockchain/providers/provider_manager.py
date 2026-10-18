import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, List, Callable, Awaitable, Dict, Any


from backend.app.config import settings
from backend.app.database import SessionLocal, BlockCursorModel
from backend.app.schemas import (
    NormalizedBlockchainEvent,
    LiveProviderStatus,
)
from backend.app.blockchain.providers.base import BlockchainProvider
from backend.app.blockchain.providers.alchemy_provider import AlchemyWebSocketProvider
from backend.app.blockchain.providers.etherscan_provider import EtherscanProvider
from backend.app.blockchain.providers.simulator_provider import SimulatorProvider

logger = logging.getLogger(__name__)

class ProviderManager:
    """
    Orchestrates blockchain ingestion providers, manages block cursor persistence,
    coordinates bounded backfill on startup, and routes events to the event pipeline.
    """
    def __init__(self):
        self.active_provider: Optional[BlockchainProvider] = None
        self.pipeline_callbacks: List[Callable[[NormalizedBlockchainEvent], Awaitable[None]]] = []
        self._initialized = False

    def get_or_create_cursor(self, network: str, db: Optional[Any] = None) -> BlockCursorModel:
        if db is None:
            db = SessionLocal()
        doc = db.block_cursors.find_one({"network": network})
        if not doc:
            now_iso = datetime.now(timezone.utc).isoformat()
            doc = {
                "_id": network,
                "network": network,
                "last_processed_block": 0,
                "last_processed_block_hash": None,
                "updated_at": now_iso
            }
            db.block_cursors.update_one({"_id": network}, {"$set": doc}, upsert=True)
        return BlockCursorModel(**doc)

    def update_cursor(self, network: str, block_number: int, block_hash: Optional[str] = None):
        db = SessionLocal()
        try:
            cursor = self.get_or_create_cursor(network, db)
            if block_number > cursor.last_processed_block:
                now_iso = datetime.now(timezone.utc).isoformat()
                update_data: Dict[str, Any] = {
                    "last_processed_block": block_number,
                    "updated_at": now_iso
                }
                if block_hash:
                    update_data["last_processed_block_hash"] = block_hash
                db.block_cursors.update_one({"_id": network}, {"$set": update_data}, upsert=True)
        except Exception as e:
            logger.warning(f"Failed to update block cursor: {e}")

    def get_persisted_cursor_block(self, network: str) -> int:
        db = SessionLocal()
        try:
            doc = db.block_cursors.find_one({"network": network})
            return doc.get("last_processed_block", 0) if doc else 0
        except Exception as e:
            logger.warning(f"Error querying cursor: {e}")
            return 0

    def register_pipeline_callback(self, cb: Callable[[NormalizedBlockchainEvent], Awaitable[None]]):
        self.pipeline_callbacks.append(cb)

    async def _on_provider_event(self, event: NormalizedBlockchainEvent):
        # Update cursor on monotonic block advance
        if event.block_number and event.block_number > 0:
            self.update_cursor(event.network, event.block_number, event.block_hash)

        # Dispatch to registered event processing pipelines
        for cb in self.pipeline_callbacks:
            try:
                await cb(event)
            except Exception as e:
                logger.error(f"Error in pipeline callback during event dispatch: {e}")

    def initialize_provider(self):
        alchemy = AlchemyWebSocketProvider(
            api_key=settings.ALCHEMY_API_KEY,
            network=settings.ETHEREUM_NETWORK,
            chain_id=settings.ETHEREUM_CHAIN_ID
        )

        etherscan = EtherscanProvider(
            api_key=settings.ETHERSCAN_API_KEY,
            base_url=settings.ETHERSCAN_BASE_URL,
            network=settings.ETHEREUM_NETWORK,
            chain_id=settings.ETHEREUM_CHAIN_ID
        )

        if alchemy.is_configured():
            logger.info("Initializing Alchemy WebSocket provider as active live ingestion provider.")
            self.active_provider = alchemy
        elif etherscan.is_configured():
            logger.info("Alchemy API key not set. Initializing Etherscan provider as fallback.")
            self.active_provider = etherscan
        elif settings.LIVE_SIMULATOR_ENABLED:
            logger.info("No external credentials set. Initializing Safe Deterministic Simulator Provider [SIMULATED].")
            self.active_provider = SimulatorProvider(
                network=settings.ETHEREUM_NETWORK,
                chain_id=settings.ETHEREUM_CHAIN_ID
            )
        else:
            logger.info("Live ingestion disabled / no provider configured.")
            self.active_provider = None

        if self.active_provider:
            self.active_provider.register_callback(self._on_provider_event)

    async def start(self):
        if not self._initialized:
            self.initialize_provider()
            self._initialized = True

        # Auto-register event pipeline if no callbacks attached
        if not self.pipeline_callbacks:
            from backend.app.services.event_pipeline import event_pipeline
            self.register_pipeline_callback(event_pipeline.process_blockchain_event)

        if self.active_provider and settings.LIVE_INGESTION_ENABLED:
            # Recover block cursor from database
            last_block = self.get_persisted_cursor_block(self.active_provider.network)
            if last_block > 0:
                logger.info(f"Recovered persisted block cursor for '{self.active_provider.network}': block {last_block}")
                self.active_provider.last_processed_block = last_block

            await self.active_provider.start()

    async def stop(self):
        if self.active_provider:
            await self.active_provider.stop()

    def get_status(self) -> LiveProviderStatus:
        if not self.active_provider:
            return LiveProviderStatus(
                provider_name="No Active Provider",
                network=settings.ETHEREUM_NETWORK,
                connected=False,
                connection_state="disabled",
                last_received_block=None,
                last_processed_block=None,
                ingestion_lag=0,
                events_received_count=0,
                events_persisted_count=0,
                error_count=0,
                last_event_time=None,
                is_simulated=False
            )
        return self.active_provider.get_status()

# Singleton provider manager
provider_manager = ProviderManager()
