import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Set, List


from backend.app.config import settings
from backend.app.database import (
    SessionLocal,
    CaseModel,
    TransactionModel,
    RawBlockchainEventModel,
)
from backend.app.schemas import (
    NormalizedBlockchainEvent,
    WebSocketMessage,
)
from backend.app.services.live_analysis_service import live_analysis_service
from backend.app.blockchain.storage import global_chain, TraceChainStorage
from backend.app.api.ws import ws_manager

logger = logging.getLogger(__name__)

class EventPipeline:
    """
    Idempotent asynchronous event processing pipeline.
    Validates, deduplicates, persists raw events, associates cases,
    enqueues background forensic jobs, and broadcasts typed real-time updates.
    """
    def __init__(self, queue_maxsize: int = 1000):
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=queue_maxsize)
        self.pending_case_jobs: Set[str] = set()
        self.running = False
        self._worker_task: Optional[asyncio.Task] = None

        # Observability & Metrics
        self.total_received = 0
        self.total_persisted = 0
        self.total_analyzed = 0
        self.error_count = 0
        self.latest_analysis_time: Optional[str] = None

    async def start(self):
        if self.running:
            return
        self.running = True
        self._worker_task = asyncio.create_task(self._analysis_worker())
        logger.info("EventPipeline asynchronous analysis worker started.")

    async def stop(self):
        self.running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        logger.info("EventPipeline stopped.")

    def get_queue_size(self) -> int:
        return self.queue.qsize()

    async def process_blockchain_event(self, event: NormalizedBlockchainEvent):
        """
        Ingests a single validated blockchain event without blocking the ingestion loop.
        """
        self.total_received += 1
        db = SessionLocal()
        try:
            # 1. Idempotent Raw Provenance Persistence
            raw_rec = {
                "_id": event.event_id,
                "event_id": event.event_id,
                "chain_id": event.chain_id,
                "network": event.network,
                "event_type": event.event_type.value if hasattr(event.event_type, "value") else str(event.event_type),
                "block_number": event.block_number,
                "block_hash": event.block_hash,
                "tx_hash": event.tx_hash,
                "log_index": event.log_index,
                "raw_payload": event.raw_provenance,
                "received_at": datetime.now(timezone.utc).isoformat()
            }
            db.raw_blockchain_events.update_one({"_id": event.event_id}, {"$set": raw_rec}, upsert=True)

            # 2. Find Relevant Open Investigation Cases
            matched_cases = self._find_matching_cases(event.from_address, event.to_address, db)

            # If no open case matches, ensure a Live Feed monitoring case exists
            if not matched_cases:
                default_case = self._get_or_create_live_monitoring_case(db)
                matched_cases = [default_case]

            # 3. Persist Normalized Transaction for Each Case
            for case in matched_cases:
                case_id = case.case_id
                tx_id = f"tx_{event.tx_hash}_{event.log_index or 'main'}"
                tx_doc = {
                    "_id": f"{case_id}:{tx_id}",
                    "case_id": case_id,
                    "tx_id": tx_id,
                    "network": case.network,
                    "data_origin": "live_provider",
                    "timestamp": event.timestamp,
                    "from_address": event.from_address,
                    "to_address": event.to_address,
                    "amount": float(event.amount),
                    "asset": event.asset,
                    "block_number": event.block_number,
                    "tx_hash": event.tx_hash,
                    "fee": float(event.fee or 0.0),
                    "log_index": event.log_index,
                    "is_reorg_removed": bool(event.is_removed),
                    "extra_metadata": event.raw_provenance
                }
                # Dedup: only count as newly persisted if document doesn't already exist
                existing = db.transactions.find_one({"_id": tx_doc["_id"]})
                db.transactions.update_one({"_id": tx_doc["_id"]}, {"$set": tx_doc}, upsert=True)
                if not existing:
                    self.total_persisted += 1

                # 4. Enqueue Asynchronous Case Analysis Job
                self._enqueue_case_job(case_id, tx_id)

            # 5. Broadcast Real-Time Transaction to Frontend
            await ws_manager.broadcast(
                WebSocketMessage(
                    event_id=event.event_id,
                    type="transaction.new",
                    timestamp=event.timestamp,
                    data={
                        "event_id": event.event_id,
                        "tx_hash": event.tx_hash,
                        "from_address": event.from_address,
                        "to_address": event.to_address,
                        "amount": event.amount,
                        "asset": event.asset,
                        "block_number": event.block_number,
                        "is_removed": event.is_removed,
                        "is_simulated": bool(event.raw_provenance.get("provider") == "SimulatorProvider")
                    }
                )
            )

        except Exception as e:
            self.error_count += 1
            logger.error(f"Error processing blockchain event '{event.event_id}': {e}")
        finally:
            db.close()

    def _find_matching_cases(self, from_addr: str, to_addr: str, db: Any) -> List[CaseModel]:
        """Finds active cases containing from_addr or to_addr in seed addresses or existing transactions."""
        norm_from = from_addr.lower()
        norm_to = to_addr.lower()

        cursor = db.cases.find()
        matched = []
        for doc in cursor:
            c = CaseModel(**doc)
            seeds = [s.lower() for s in c.seed_addresses]
            if norm_from in seeds or norm_to in seeds:
                matched.append(c)
        return matched

    def _get_or_create_live_monitoring_case(self, db: Any) -> CaseModel:
        """Retrieves or creates the default live monitoring case."""
        case_id = "CASE-ETH-LIVE-FEED"
        doc = db.cases.find_one({"$or": [{"_id": case_id}, {"case_id": case_id}]})
        if not doc:
            now_iso = datetime.now(timezone.utc).isoformat()
            doc = {
                "_id": case_id,
                "case_id": case_id,
                "case_name": "Ethereum Live Transaction Stream",
                "description": "Live real-time blockchain monitoring case for inbound Ethereum evidence.",
                "network": "ethereum",
                "data_source": "live_ethereum_stream",
                "status": "created",
                "seed_addresses": [
                    "0x71c7656ec7ab88b098defb751b7401b5f6d8976f",
                    "0x28c6c06298d514db089934071355e5743bf21d60"
                ],
                "tx_count": 0,
                "evidence_count": 0,
                "summary": None,
                "created_at": now_iso,
                "updated_at": now_iso
            }
            db.cases.update_one({"_id": case_id}, {"$set": doc}, upsert=True)

            # Mine genesis audit block for live case
            b = global_chain.mine_and_add_block(
                event_type="LIVE_CASE_INITIALIZED",
                payload={"case_id": case_id, "name": doc["case_name"]},
                case_id=case_id
            )
            TraceChainStorage.persist_block(b, db)

        return CaseModel(**doc)

    def _enqueue_case_job(self, case_id: str, trigger_tx_id: str):
        if case_id in self.pending_case_jobs:
            return  # Suppress duplicate pending job for same case

        try:
            self.queue.put_nowait((case_id, trigger_tx_id))
            self.pending_case_jobs.add(case_id)
        except asyncio.QueueFull:
            logger.warning(f"Analysis queue full! Dropping incremental re-analysis for {case_id}")

    async def _analysis_worker(self):
        """Dedicated background worker executing forensic analysis without blocking ingestion."""
        while self.running:
            try:
                case_id, trigger_tx_id = await self.queue.get()
                self.pending_case_jobs.discard(case_id)

                db = SessionLocal()
                try:
                    result = live_analysis_service.analyze_case_incremental(case_id, db, trigger_tx_id)
                    self.total_analyzed += 1
                    self.latest_analysis_time = datetime.now(timezone.utc).isoformat()

                    # Broadcast incremental updates to clients subscribed to this case
                    await ws_manager.broadcast_to_case(
                        case_id=case_id,
                        message=WebSocketMessage(
                            event_id=f"upd_{datetime.now(timezone.utc).timestamp()}",
                            type="graph.updated",
                            timestamp=self.latest_analysis_time,
                            case_id=case_id,
                            data={
                                "case_id": case_id,
                                "graph": result["graph"],
                                "summary": result["summary"]
                            }
                        )
                    )

                    await ws_manager.broadcast_to_case(
                        case_id=case_id,
                        message=WebSocketMessage(
                            event_id=f"lead_{datetime.now(timezone.utc).timestamp()}",
                            type="lead.created",
                            timestamp=self.latest_analysis_time,
                            case_id=case_id,
                            data={
                                "case_id": case_id,
                                "leads": result["ranked_leads"]
                            }
                        )
                    )

                    await ws_manager.broadcast_to_case(
                        case_id=case_id,
                        message=WebSocketMessage(
                            event_id=f"fc_{datetime.now(timezone.utc).timestamp()}",
                            type="forecast.updated",
                            timestamp=self.latest_analysis_time,
                            case_id=case_id,
                            data={
                                "case_id": case_id,
                                "forecast": result["cashout_forecast"]
                            }
                        )
                    )

                    await ws_manager.broadcast(
                        WebSocketMessage(
                            event_id=f"aud_{result['audit_block']['hash'][:16]}",
                            type="audit.updated",
                            timestamp=self.latest_analysis_time,
                            case_id=case_id,
                            data={
                                "block_index": result["audit_block"]["index"],
                                "block_hash": result["audit_block"]["hash"],
                                "case_id": case_id
                            }
                        )
                    )

                except Exception as e:
                    self.error_count += 1
                    logger.error(f"Error in background case analysis for '{case_id}': {e}")
                finally:
                    db.close()
                    self.queue.task_done()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in analysis worker loop: {e}")
                await asyncio.sleep(1.0)

event_pipeline = EventPipeline()
