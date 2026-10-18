from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Callable, Awaitable
from backend.app.schemas import NormalizedBlockchainEvent, BlockchainEventType, LiveProviderStatus

ERC20_TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

KNOWN_ERC20_TOKENS = {
    "0xdac17f958d2ee523a2206206994597c13d831ec7": ("USDT", 6),
    "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48": ("USDC", 6),
    "0x6b175474e89094c44da98b954eedeac495271d0f": ("DAI", 18),
    "0x2260fac5e5542a773aa44fbcfedf7c193bc2c599": ("WBTC", 8),
    "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2": ("WETH", 18),
}

def decode_hex_int(val: Any) -> int:
    """Decodes hex or int to Python integer."""
    if val is None:
        return 0
    if isinstance(val, int):
        return val
    val_str = str(val).strip()
    if val_str.startswith("0x") or val_str.startswith("0X"):
        try:
            return int(val_str, 16)
        except ValueError:
            return 0
    try:
        return int(val_str)
    except ValueError:
        return 0

def format_address(addr: Any) -> str:
    """Normalizes address to lowercase 0x-prefixed 40-hex string."""
    if not addr:
        return "0x0000000000000000000000000000000000000000"
    raw = str(addr).strip().lower()
    if raw.startswith("0x"):
        raw = raw[2:]
    # If 32-byte topic (64 chars), take last 40 chars
    if len(raw) == 64:
        raw = raw[-40:]
    return f"0x{raw.zfill(40)}"

def parse_timestamp_iso(ts_val: Any) -> str:
    """Converts hex, int unix timestamp, or string to standard ISO-8601 UTC."""
    if ts_val is None:
        return datetime.now(timezone.utc).isoformat()
    if isinstance(ts_val, str) and ("T" in ts_val or "-" in ts_val):
        return ts_val.replace("Z", "+00:00")
    unix_secs = decode_hex_int(ts_val)
    if unix_secs <= 0:
        return datetime.now(timezone.utc).isoformat()
    return datetime.fromtimestamp(unix_secs, timezone.utc).isoformat()

def decode_erc20_log(
    log: Dict[str, Any],
    chain_id: int = 1,
    network: str = "ethereum",
    fallback_timestamp: Optional[str] = None
) -> Optional[NormalizedBlockchainEvent]:
    """
    Decodes an Ethereum log into a NormalizedBlockchainEvent if it matches ERC-20 Transfer.
    """
    topics = log.get("topics", [])
    if not topics or len(topics) < 3:
        return None

    topic0 = str(topics[0]).lower()
    if topic0 != ERC20_TRANSFER_TOPIC.lower():
        return None

    contract_addr = format_address(log.get("address"))
    from_addr = format_address(topics[1])
    to_addr = format_address(topics[2])

    # Decode amount from data hex
    data_hex = log.get("data", "0x0")
    raw_amount = decode_hex_int(data_hex)

    token_symbol, decimals = KNOWN_ERC20_TOKENS.get(contract_addr, ("ERC20", 18))
    norm_amount = raw_amount / (10 ** decimals)

    block_num = decode_hex_int(log.get("blockNumber"))
    block_hash = str(log.get("blockHash", ""))
    tx_hash = str(log.get("transactionHash", ""))
    log_index = decode_hex_int(log.get("logIndex"))
    is_removed = bool(log.get("removed", False))

    timestamp = parse_timestamp_iso(log.get("timeStamp") or fallback_timestamp)

    event_id = f"eth_{chain_id}_{block_num}_{tx_hash}_{log_index}"

    return NormalizedBlockchainEvent(
        event_id=event_id,
        chain_id=chain_id,
        network=network,
        event_type=BlockchainEventType.REORG_REMOVED if is_removed else BlockchainEventType.ERC20_TRANSFER,
        block_number=block_num,
        block_hash=block_hash,
        tx_hash=tx_hash,
        log_index=log_index,
        timestamp=timestamp,
        from_address=from_addr,
        to_address=to_addr,
        amount=round(norm_amount, 6),
        asset=token_symbol,
        contract_address=contract_addr,
        fee=0.0,
        is_removed=is_removed,
        raw_provenance={
            "provider": "log_decoder",
            "logIndex": log_index,
            "raw_value_wei": raw_amount,
            "contract": contract_addr,
            "decimals": decimals
        }
    )

def normalize_native_transaction(
    tx: Dict[str, Any],
    block: Dict[str, Any],
    chain_id: int = 1,
    network: str = "ethereum"
) -> NormalizedBlockchainEvent:
    """
    Normalizes a full Ethereum transaction into a NormalizedBlockchainEvent.
    """
    tx_hash = str(tx.get("hash", ""))
    from_addr = format_address(tx.get("from"))
    to_addr = format_address(tx.get("to"))
    
    val_wei = decode_hex_int(tx.get("value"))
    val_eth = val_wei / 1e18

    gas = decode_hex_int(tx.get("gas"))
    gas_price = decode_hex_int(tx.get("gasPrice"))
    fee_eth = (gas * gas_price) / 1e18 if gas and gas_price else 0.0

    block_num = decode_hex_int(tx.get("blockNumber") or block.get("number"))
    block_hash = str(tx.get("blockHash") or block.get("hash", ""))
    timestamp = parse_timestamp_iso(block.get("timestamp"))

    event_id = f"eth_{chain_id}_{block_num}_{tx_hash}_native"

    return NormalizedBlockchainEvent(
        event_id=event_id,
        chain_id=chain_id,
        network=network,
        event_type=BlockchainEventType.NATIVE_TRANSFER,
        block_number=block_num,
        block_hash=block_hash,
        tx_hash=tx_hash,
        log_index=None,
        timestamp=timestamp,
        from_address=from_addr,
        to_address=to_addr,
        amount=round(val_eth, 6),
        asset="ETH",
        contract_address=None,
        fee=round(fee_eth, 6),
        is_removed=False,
        raw_provenance={
            "provider": "native_decoder",
            "gas": gas,
            "gasPrice": gas_price,
            "raw_value_wei": val_wei
        }
    )

class BlockchainProvider(ABC):
    """
    Abstract interface for blockchain real-time data providers.
    Supports WebSocket streaming, bounded polling, log subscriptions, and health metrics.
    """
    def __init__(self, network: str = "ethereum", chain_id: int = 1):
        self.network = network
        self.chain_id = chain_id
        self.event_callbacks: List[Callable[[NormalizedBlockchainEvent], Awaitable[None]]] = []

    def register_callback(self, cb: Callable[[NormalizedBlockchainEvent], Awaitable[None]]):
        self.event_callbacks.append(cb)

    async def emit_event(self, event: NormalizedBlockchainEvent):
        for cb in self.event_callbacks:
            try:
                await cb(event)
            except Exception as e:
                pass

    @abstractmethod
    def is_configured(self) -> bool:
        """Returns True if valid provider credentials/URLs are set."""
        pass

    @abstractmethod
    async def start(self):
        """Starts real-time subscription or polling loop."""
        pass

    @abstractmethod
    async def stop(self):
        """Stops background tasks and closes connections."""
        pass

    @abstractmethod
    def get_status(self) -> LiveProviderStatus:
        """Returns health metrics, connection state, and block lag."""
        pass

    @abstractmethod
    async def backfill_blocks(self, start_block: int, end_block: int) -> int:
        """Backfills missed blocks bounded by limit."""
        pass
