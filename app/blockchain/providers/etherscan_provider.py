import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
import httpx

from backend.app.config import settings
from backend.app.schemas import (
    NormalizedBlockchainEvent,
    BlockchainEventType,
    LiveProviderStatus,
)
from backend.app.blockchain.providers.base import (
    BlockchainProvider,
    decode_hex_int,
    parse_timestamp_iso,
    format_address,
)

logger = logging.getLogger(__name__)

class EtherscanProvider(BlockchainProvider):
    """
    Etherscan REST API provider.
    Serves as an external HTTP provider / fallback when WebSocket credentials are not available.
    """
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        network: str = "ethereum",
        chain_id: int = 1
    ):
        super().__init__(network=network, chain_id=chain_id)
        self.api_key = api_key or settings.ETHERSCAN_API_KEY
        self.base_url = base_url or settings.ETHERSCAN_BASE_URL
        self.running = False
        self._task: Optional[asyncio.Task] = None

        self.connected = False
        self.connection_state = "offline"
        self.last_received_block: Optional[int] = None
        self.last_processed_block: Optional[int] = None
        self.events_received_count = 0
        self.events_persisted_count = 0
        self.error_count = 0
        self.last_event_time: Optional[str] = None

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip() and self.api_key != "YOUR_ETHERSCAN_API_KEY")

    async def start(self):
        if self.running:
            return
        self.running = True
        self.connection_state = "connected" if self.is_configured() else "unconfigured"
        self.connected = self.is_configured()
        logger.info(f"EtherscanProvider started for network '{self.network}'.")

    async def stop(self):
        self.running = False
        self.connected = False
        self.connection_state = "offline"
        if self._task:
            self._task.cancel()
        logger.info("EtherscanProvider stopped.")

    def get_status(self) -> LiveProviderStatus:
        lag = 0
        if self.last_received_block and self.last_processed_block:
            lag = max(0, self.last_received_block - self.last_processed_block)

        return LiveProviderStatus(
            provider_name="Etherscan REST Provider",
            network=self.network,
            connected=self.connected,
            connection_state=self.connection_state,
            last_received_block=self.last_received_block,
            last_processed_block=self.last_processed_block,
            ingestion_lag=lag,
            events_received_count=self.events_received_count,
            events_persisted_count=self.events_persisted_count,
            error_count=self.error_count,
            last_event_time=self.last_event_time,
            is_simulated=False
        )

    async def fetch_block_number(self) -> Optional[int]:
        if not self.is_configured():
            return None
        params = {"module": "proxy", "action": "eth_blockNumber", "apikey": self.api_key}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(self.base_url, params=params)
                if res.status_code == 200:
                    data = res.json()
                    hex_num = data.get("result")
                    return decode_hex_int(hex_num)
        except Exception as e:
            self.error_count += 1
            logger.warning(f"Etherscan blockNumber query error: {e}")
        return None

    async def backfill_blocks(self, start_block: int, end_block: int) -> int:
        return 0
