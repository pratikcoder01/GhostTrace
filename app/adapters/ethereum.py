import logging
from typing import List, Dict, Any, Optional, Tuple
import httpx
from backend.app.schemas import TransactionRecord, NetworkType, DataOrigin
from backend.app.config import settings

logger = logging.getLogger(__name__)

class EthereumAdapter:
    """
    Read-only Ethereum adapter via Etherscan API.
    Operates safely with rate-limiting, timeouts, and graceful offline fallback.
    """
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or settings.ETHERSCAN_API_KEY
        self.base_url = base_url or settings.ETHERSCAN_BASE_URL
        self.timeout = 10.0

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip() and self.api_key != "YOUR_ETHERSCAN_API_KEY")

    async def fetch_account_transactions(
        self,
        address: str,
        max_txs: int = 50
    ) -> Tuple[List[TransactionRecord], Dict[str, Any]]:
        """
        Fetches native transactions for a given Ethereum address.
        Returns (transactions, provider_metadata).
        """
        if not self.is_configured():
            return [], {
                "status": "offline_mode",
                "message": "Etherscan API key not configured. External live retrieval disabled.",
                "configured": False
            }

        params = {
            "module": "account",
            "action": "txlist",
            "address": address,
            "startblock": 0,
            "endblock": 99999999,
            "page": 1,
            "offset": max_txs,
            "sort": "desc",
            "apikey": self.api_key
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(self.base_url, params=params)
                if response.status_code != 200:
                    return [], {
                        "status": "error",
                        "status_code": response.status_code,
                        "error": f"Provider HTTP {response.status_code}"
                    }

                data = response.json()
                if data.get("status") != "1" and data.get("message") != "No transactions found":
                    return [], {
                        "status": "provider_error",
                        "message": data.get("result", "Unknown Etherscan error")
                    }

                results = data.get("result", [])
                tx_records: List[TransactionRecord] = []
                for item in results:
                    val_wei = float(item.get("value", 0))
                    val_eth = val_wei / 1e18
                    gas_used = float(item.get("gasUsed", 0))
                    gas_price = float(item.get("gasPrice", 0))
                    fee_eth = (gas_used * gas_price) / 1e18

                    tx = TransactionRecord(
                        tx_id=f"eth_{item.get('hash')}",
                        network=NetworkType.ETHEREUM,
                        data_origin=DataOrigin.LIVE_PROVIDER,
                        timestamp=str(item.get("timeStamp")),
                        from_address=str(item.get("from")).lower(),
                        to_address=str(item.get("to", "")).lower(),
                        amount=val_eth,
                        asset="ETH",
                        block_number=int(item.get("blockNumber", 0)),
                        tx_hash=item.get("hash"),
                        fee=fee_eth,
                        extra_metadata={
                            "is_error": item.get("isError") == "1",
                            "contract_address": item.get("contractAddress")
                        }
                    )
                    tx_records.append(tx)

                return tx_records, {
                    "status": "success",
                    "retrieved_count": len(tx_records),
                    "provider": "Etherscan",
                    "address": address
                }

        except httpx.RequestError as exc:
            logger.warning(f"Etherscan request error for {address}: {exc}")
            return [], {
                "status": "network_error",
                "error": str(exc)
            }
