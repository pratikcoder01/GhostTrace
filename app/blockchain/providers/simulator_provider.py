import asyncio
import hashlib
import logging
import random
from datetime import datetime, timezone
from typing import Optional, List
from backend.app.schemas import (
    NormalizedBlockchainEvent,
    BlockchainEventType,
    LiveProviderStatus,
)
from backend.app.blockchain.providers.base import BlockchainProvider

logger = logging.getLogger(__name__)

# Sample addresses modeled after active investigation wallets and exchange endpoints
SIMULATED_WALLETS = [
    ("0x71c7656ec7ab88b098defb751b7401b5f6d8976f", "Investigation Victim 01"),
    ("0x28c6c06298d514db089934071355e5743bf21d60", "Binance 14 Hot Wallet"),
    ("0xdac17f958d2ee523a2206206994597c13d831ec7", "Tether USD (ERC-20 Contract)"),
    ("0x3f5ce5fbfe3e9af3971dd833d26ba9b5c936f0be", "Binance 8 Deposit Gate"),
    ("0x53d28326de2ab7740b6d66f34860699662702f7e", "Identified Mixer Inflow Node"),
    ("0xdfd5293d8e347dff59e77156952a429c1a3ab574", "High-Velocity Transit Wallet"),
    ("0xbe0eb53f46cd790cd13851d5eff43d12404d33e8", "Binance 7 Cold Storage"),
    ("0x1111111254fb6c44bac0bed2854e76f90643097d", "1inch Aggregator V5"),
]

class SimulatorProvider(BlockchainProvider):
    """
    Safe, deterministic real-time Ethereum simulator.
    Operates when real provider credentials (Alchemy/Etherscan) are absent or in development mode.
    All events and statuses are explicitly marked with `is_simulated = True`.
    """
    def __init__(
        self,
        network: str = "ethereum",
        chain_id: int = 1,
        block_interval: float = 6.0,
        start_block: int = 21000000
    ):
        super().__init__(network=network, chain_id=chain_id)
        self.block_interval = block_interval
        self.current_block = start_block
        self.last_block_hash = "0x" + hashlib.sha256(b"genesis_sim_block").hexdigest()

        self.running = False
        self._task: Optional[asyncio.Task] = None

        # Metrics
        self.connected = False
        self.connection_state = "offline"
        self.last_received_block: Optional[int] = None
        self.last_processed_block: Optional[int] = None
        self.events_received_count = 0
        self.events_persisted_count = 0
        self.error_count = 0
        self.last_event_time: Optional[str] = None

    def is_configured(self) -> bool:
        return True

    async def start(self):
        if self.running:
            return
        self.running = True
        self.connected = True
        self.connection_state = "simulated_stream_active"
        self._task = asyncio.create_task(self._simulation_loop())
        logger.info(f"SimulatorProvider started (interval={self.block_interval}s, start_block={self.current_block}). [CLEARLY LABELED AS SIMULATION]")

    async def stop(self):
        self.running = False
        self.connected = False
        self.connection_state = "offline"
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("SimulatorProvider stopped.")

    def get_status(self) -> LiveProviderStatus:
        return LiveProviderStatus(
            provider_name="Safe Deterministic Ethereum Simulator [SIMULATION ONLY]",
            network=self.network,
            connected=self.connected,
            connection_state=self.connection_state,
            last_received_block=self.last_received_block,
            last_processed_block=self.last_processed_block,
            ingestion_lag=0,
            events_received_count=self.events_received_count,
            events_persisted_count=self.events_persisted_count,
            error_count=self.error_count,
            last_event_time=self.last_event_time,
            is_simulated=True
        )

    async def _simulation_loop(self):
        while self.running:
            try:
                await asyncio.sleep(self.block_interval)
                if not self.running:
                    break

                self.current_block += 1
                now_iso = datetime.now(timezone.utc).isoformat()
                block_hash = "0x" + hashlib.sha256(f"sim_block_{self.current_block}".encode()).hexdigest()

                self.last_received_block = self.current_block
                self.last_block_hash = block_hash

                # 1. Generate 1 to 3 realistic simulated transactions
                num_txs = random.randint(1, 3)
                for i in range(num_txs):
                    sender_tuple = random.choice(SIMULATED_WALLETS)
                    receiver_tuple = random.choice([w for w in SIMULATED_WALLETS if w[0] != sender_tuple[0]])

                    tx_hash = "0x" + hashlib.sha256(f"sim_tx_{self.current_block}_{i}_{random.random()}".encode()).hexdigest()

                    # Alternates between native ETH and ERC-20 transfers
                    is_erc20 = random.choice([True, False])
                    if is_erc20:
                        asset = random.choice(["USDT", "USDC", "DAI"])
                        amount = round(random.uniform(500.0, 50000.0), 2)
                        event = NormalizedBlockchainEvent(
                            event_id=f"sim_eth_{self.chain_id}_{self.current_block}_{tx_hash}_{i}",
                            chain_id=self.chain_id,
                            network="ethereum",
                            event_type=BlockchainEventType.ERC20_TRANSFER,
                            block_number=self.current_block,
                            block_hash=block_hash,
                            tx_hash=tx_hash,
                            log_index=i,
                            timestamp=now_iso,
                            from_address=sender_tuple[0],
                            to_address=receiver_tuple[0],
                            amount=amount,
                            asset=asset,
                            contract_address="0xdac17f958d2ee523a2206206994597c13d831ec7" if asset == "USDT" else "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
                            fee=round(random.uniform(0.001, 0.005), 6),
                            is_removed=False,
                            raw_provenance={
                                "provider": "SimulatorProvider",
                                "label": "SAFE_CACHED_OR_SIMULATED_EVENT",
                                "sender_label": sender_tuple[1],
                                "receiver_label": receiver_tuple[1]
                            }
                        )
                    else:
                        amount = round(random.uniform(0.5, 32.0), 4)
                        event = NormalizedBlockchainEvent(
                            event_id=f"sim_eth_{self.chain_id}_{self.current_block}_{tx_hash}_native",
                            chain_id=self.chain_id,
                            network="ethereum",
                            event_type=BlockchainEventType.NATIVE_TRANSFER,
                            block_number=self.current_block,
                            block_hash=block_hash,
                            tx_hash=tx_hash,
                            log_index=None,
                            timestamp=now_iso,
                            from_address=sender_tuple[0],
                            to_address=receiver_tuple[0],
                            amount=amount,
                            asset="ETH",
                            contract_address=None,
                            fee=round(random.uniform(0.0005, 0.003), 6),
                            is_removed=False,
                            raw_provenance={
                                "provider": "SimulatorProvider",
                                "label": "SAFE_CACHED_OR_SIMULATED_EVENT",
                                "sender_label": sender_tuple[1],
                                "receiver_label": receiver_tuple[1]
                            }
                        )

                    self.events_received_count += 1
                    self.last_event_time = now_iso
                    await self.emit_event(event)

                self.last_processed_block = self.current_block

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.error_count += 1
                logger.error(f"SimulatorProvider error: {e}")

    async def inject_event(
        self,
        from_address: str,
        to_address: str,
        amount: float = 1.0,
        asset: str = "ETH",
        is_removed: bool = False
    ) -> NormalizedBlockchainEvent:
        """Allows injecting an explicit event on-demand for integration testing and demo."""
        self.current_block += 1
        now_iso = datetime.now(timezone.utc).isoformat()
        tx_hash = "0x" + hashlib.sha256(f"manual_{self.current_block}_{random.random()}".encode()).hexdigest()
        block_hash = "0x" + hashlib.sha256(f"manual_block_{self.current_block}".encode()).hexdigest()

        event = NormalizedBlockchainEvent(
            event_id=f"sim_eth_{self.chain_id}_{self.current_block}_{tx_hash}_{'removed' if is_removed else 'tx'}",
            chain_id=self.chain_id,
            network="ethereum",
            event_type=BlockchainEventType.REORG_REMOVED if is_removed else BlockchainEventType.NATIVE_TRANSFER,
            block_number=self.current_block,
            block_hash=block_hash,
            tx_hash=tx_hash,
            log_index=0 if is_removed else None,
            timestamp=now_iso,
            from_address=from_address.lower(),
            to_address=to_address.lower(),
            amount=amount,
            asset=asset,
            contract_address=None,
            fee=0.001,
            is_removed=is_removed,
            raw_provenance={
                "provider": "SimulatorProvider",
                "label": "MANUAL_SIMULATED_TEST_INJECTION",
                "is_reorg_simulation": is_removed
            }
        )
        self.events_received_count += 1
        self.last_event_time = now_iso
        self.last_received_block = self.current_block
        self.last_processed_block = self.current_block
        await self.emit_event(event)
        return event

    async def backfill_blocks(self, start_block: int, end_block: int) -> int:
        return 0
