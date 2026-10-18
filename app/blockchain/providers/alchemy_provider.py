import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import httpx
import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

from backend.app.config import settings
from backend.app.schemas import (
    NormalizedBlockchainEvent,
    BlockchainEventType,
    LiveProviderStatus,
)
from backend.app.blockchain.providers.base import (
    BlockchainProvider,
    decode_hex_int,
    decode_erc20_log,
    normalize_native_transaction,
    ERC20_TRANSFER_TOPIC,
)

logger = logging.getLogger(__name__)

class AlchemyWebSocketProvider(BlockchainProvider):
    """
    Production-grade Alchemy WebSocket & JSON-RPC provider for Ethereum.
    Subscribes to newHeads and filtered ERC-20 Transfer contract logs.
    Handles exponential backoff, rate limits, reorgs, and bounded backfill.
    """
    def __init__(
        self,
        api_key: Optional[str] = None,
        ws_url: Optional[str] = None,
        http_url: Optional[str] = None,
        network: str = "ethereum",
        chain_id: int = 1
    ):
        super().__init__(network=network, chain_id=chain_id)
        self.api_key = api_key or settings.ALCHEMY_API_KEY
        self.ws_url = ws_url or settings.ALCHEMY_WS_URL
        self.http_url = http_url or settings.ALCHEMY_HTTP_URL
        
        # Build standard Alchemy URLs if API key provided and URL empty
        if self.api_key and not self.ws_url:
            self.ws_url = f"wss://eth-{settings.ETHEREUM_NETWORK}.g.alchemy.com/v2/{self.api_key}"
        if self.api_key and not self.http_url:
            self.http_url = f"https://eth-{settings.ETHEREUM_NETWORK}.g.alchemy.com/v2/{self.api_key}"

        self.running = False
        self._task: Optional[asyncio.Task] = None
        self._ws: Optional[Any] = None

        # Metrics & Health
        self.connected = False
        self.connection_state = "offline"
        self.last_received_block: Optional[int] = None
        self.last_processed_block: Optional[int] = None
        self.last_block_hash: Optional[str] = None
        self.events_received_count = 0
        self.events_persisted_count = 0
        self.error_count = 0
        self.last_event_time: Optional[str] = None

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip() and self.api_key != "YOUR_ALCHEMY_API_KEY")

    async def start(self):
        if self.running:
            return
        self.running = True
        self._task = asyncio.create_task(self._listen_loop())
        logger.info(f"AlchemyWebSocketProvider started for network '{self.network}'.")

    async def stop(self):
        self.running = False
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self.connected = False
        self.connection_state = "offline"
        logger.info("AlchemyWebSocketProvider stopped.")

    def get_status(self) -> LiveProviderStatus:
        lag = 0
        if self.last_received_block and self.last_processed_block:
            lag = max(0, self.last_received_block - self.last_processed_block)

        return LiveProviderStatus(
            provider_name="Alchemy WebSocket Provider",
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

    async def _listen_loop(self):
        backoff = 1.0
        max_backoff = 30.0

        while self.running:
            if not self.is_configured():
                self.connection_state = "unconfigured"
                await asyncio.sleep(5.0)
                continue

            try:
                self.connection_state = "connecting"
                logger.info(f"Connecting to Alchemy WS endpoint: {self.ws_url.split('/v2/')[0]}/v2/***")
                async with websockets.connect(self.ws_url, ping_interval=20, ping_timeout=15) as ws:
                    self._ws = ws
                    self.connected = True
                    self.connection_state = "connected"
                    backoff = 1.0
                    logger.info("Successfully connected to Alchemy WebSocket stream.")

                    # 1. Subscribe to newHeads
                    await ws.send(json.dumps({
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "eth_subscribe",
                        "params": ["newHeads"]
                    }))

                    # 2. Subscribe to ERC-20 Transfer logs
                    await ws.send(json.dumps({
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "eth_subscribe",
                        "params": ["logs", {"topics": [ERC20_TRANSFER_TOPIC]}]
                    }))

                    # Message loop
                    async for raw_msg in ws:
                        if not self.running:
                            break
                        await self._handle_ws_message(raw_msg)

            except (ConnectionClosed, WebSocketException, OSError) as exc:
                self.connected = False
                self.connection_state = "reconnecting"
                self.error_count += 1
                logger.warning(f"Alchemy WS disconnect ({exc}). Reconnecting in {backoff:.1f}s...")
                await asyncio.sleep(backoff)
                backoff = min(max_backoff, backoff * 2.0)
            except Exception as e:
                self.connected = False
                self.connection_state = "error"
                self.error_count += 1
                logger.error(f"Unexpected Alchemy provider error: {e}")
                await asyncio.sleep(backoff)
                backoff = min(max_backoff, backoff * 2.0)

    async def _handle_ws_message(self, raw_msg: str):
        try:
            msg = json.loads(raw_msg)
            # Subscription confirmation or ping
            if "params" not in msg:
                return

            params = msg.get("params", {})
            result = params.get("result", {})

            # Check if block header
            if "number" in result and "parentHash" in result:
                await self._process_block_header(result)
            # Check if event log
            elif "topics" in result:
                await self._process_log(result)

        except Exception as e:
            self.error_count += 1
            logger.error(f"Error handling Alchemy WS message: {e}")

    async def _process_block_header(self, header: Dict[str, Any]):
        block_num = decode_hex_int(header.get("number"))
        block_hash = str(header.get("hash", ""))
        self.last_received_block = block_num
        self.last_block_hash = block_hash

        # Reorg detection: verify parentHash if previous block known
        parent_hash = str(header.get("parentHash", ""))
        if self.last_block_hash and parent_hash and self.last_block_hash != parent_hash:
            logger.warning(f"Chain reorganization detected at block {block_num}! Parent hash {parent_hash} != {self.last_block_hash}")

        # Fetch full block with transactions via JSON-RPC
        full_block = await self.fetch_block_by_number(block_num, full_tx=True)
        if full_block and "transactions" in full_block:
            txs = full_block.get("transactions", [])
            for tx in txs:
                if isinstance(tx, dict) and decode_hex_int(tx.get("value")) > 0:
                    norm_tx = normalize_native_transaction(
                        tx=tx,
                        block=full_block,
                        chain_id=self.chain_id,
                        network=self.network
                    )
                    self.events_received_count += 1
                    self.last_event_time = datetime.now(timezone.utc).isoformat()
                    await self.emit_event(norm_tx)

        self.last_processed_block = block_num

    async def _process_log(self, log_dict: Dict[str, Any]):
        norm_event = decode_erc20_log(
            log=log_dict,
            chain_id=self.chain_id,
            network=self.network
        )
        if norm_event:
            self.events_received_count += 1
            self.last_event_time = datetime.now(timezone.utc).isoformat()
            await self.emit_event(norm_event)

    async def fetch_block_by_number(self, block_num: int, full_tx: bool = True) -> Optional[Dict[str, Any]]:
        """Fetches full block over HTTP JSON-RPC."""
        if not self.http_url:
            return None
        hex_num = hex(block_num)
        payload = {
            "jsonrpc": "2.0",
            "id": 10,
            "method": "eth_getBlockByNumber",
            "params": [hex_num, full_tx]
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(self.http_url, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    return data.get("result")
                elif res.status_code == 429:
                    logger.warning("Alchemy HTTP rate limit encountered (HTTP 429).")
        except Exception as e:
            logger.warning(f"Failed to fetch block {block_num}: {e}")
        return None

    async def backfill_blocks(self, start_block: int, end_block: int) -> int:
        """
        Backfills missed blocks bounded by BACKFILL_BLOCK_LIMIT.
        """
        if start_block > end_block:
            return 0
        limit = min(settings.BACKFILL_BLOCK_LIMIT, end_block - start_block + 1)
        target_start = max(start_block, end_block - limit + 1)
        count = 0

        logger.info(f"Backfilling blocks from {target_start} to {end_block} (limit {limit})...")
        for b in range(target_start, end_block + 1):
            block_data = await self.fetch_block_by_number(b, full_tx=True)
            if block_data:
                for tx in block_data.get("transactions", []):
                    if isinstance(tx, dict) and decode_hex_int(tx.get("value")) > 0:
                        norm_tx = normalize_native_transaction(
                            tx=tx,
                            block=block_data,
                            chain_id=self.chain_id,
                            network=self.network
                        )
                        self.events_received_count += 1
                        await self.emit_event(norm_tx)
                count += 1
                self.last_processed_block = b

        return count
