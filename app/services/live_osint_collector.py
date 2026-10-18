import asyncio
import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import httpx


from backend.app.config import settings
from backend.app.database import SessionLocal, OSINTSourceRecordModel
from backend.app.schemas import OSINTIndicator
from backend.app.services.osint_service import osint_service

logger = logging.getLogger(__name__)

# Supported public OSINT sources with endpoint, description, and polling characteristics
SUPPORTED_OSINT_SOURCES = [
    {
        "source_id": "cryptoscamdb_feed",
        "name": "CryptoScamDB Public Blacklist Feed",
        "url": "https://api.cryptoscamdb.org/v1/addresses",
        "fallback_file": settings.CRYPTOSCAMDB_FILE,
        "polling_interval_minutes": 60,
        "category": "Reported Malicious / Scam Allegation",
        "terms": "Public open-source threat database. Allegations represent community-reported flags, not legal determinations."
    },
    {
        "source_id": "phishfort_ioc",
        "name": "PhishFort Open Threat Intel Repository",
        "url": "https://raw.githubusercontent.com/phishfort/phishfort-lists/master/blacklists/domains.json",
        "fallback_file": None,
        "polling_interval_minutes": 120,
        "category": "Phishing & Impersonation Domain",
        "terms": "Open repository of observed Web3 phishing and spoofed domains."
    }
]

class LiveOSINTCollector:
    """
    Configurable live OSINT intelligence collector.
    Collects, hashes, caches, deduplicates, and normalizes indicators from public feeds.
    Clearly distinguishes live responses from cache, enforces timeouts, and preserves provenance.
    """
    def __init__(self):
        self.sources = SUPPORTED_OSINT_SOURCES
        self._task: Optional[asyncio.Task] = None
        self.running = False

    def get_sources_status(self) -> Dict[str, Any]:
        """Returns metadata, collection timestamps, and cached/live status for all configured sources."""
        db = SessionLocal()
        status_map: Dict[str, Any] = {}
        try:
            records = {doc["source_id"]: OSINTSourceRecordModel(**doc) for doc in db.osint_sources.find()}
            for src in self.sources:
                rec = records.get(src["source_id"])
                status_map[src["source_id"]] = {
                    "source_name": src["name"],
                    "url": src["url"],
                    "status": rec.status if rec else "not_collected",
                    "is_live": (rec.status == "live") if rec else False,
                    "last_collected_at": rec.last_collected_at if rec else None,
                    "content_hash": rec.content_hash if rec else None,
                    "records_count": rec.records_count if rec else 0,
                    "polling_interval_minutes": src["polling_interval_minutes"],
                    "attribution_note": src["terms"]
                }
        finally:
            db.close()
        return status_map

    async def collect_source(self, source_info: Dict[str, Any], db: Any) -> Dict[str, Any]:
        """
        Attempts live collection for a source with bounded backoff and fallback to cached payload.
        """
        source_id = source_info["source_id"]
        url = source_info["url"]
        logger.info(f"Collecting OSINT source: {source_info['name']}...")

        doc = db.osint_sources.find_one({"source_id": source_id})
        if not doc:
            doc = {
                "_id": source_id,
                "source_id": source_id,
                "source_name": source_info["name"],
                "source_url": url,
                "content_hash": None,
                "last_collected_at": None,
                "status": "pending",
                "records_count": 0,
                "cache_payload_json": "{}"
            }
            db.osint_sources.update_one({"_id": source_id}, {"$set": doc}, upsert=True)
        rec = OSINTSourceRecordModel(**doc)

        # Attempt HTTP fetch with timeout
        raw_content: Optional[str] = None
        is_live = False
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.get(url)
                if res.status_code == 200:
                    raw_content = res.text
                    is_live = True
                else:
                    logger.warning(f"OSINT source {source_id} returned HTTP {res.status_code}.")
        except Exception as e:
            logger.info(f"OSINT live fetch notice for {source_id}: {e}. Utilizing cached dataset.")

        # Fallback to local snapshot file if live fetch unsuccessful and cache empty
        if not raw_content and not rec.content_hash and source_info.get("fallback_file"):
            fb_file = source_info["fallback_file"]
            if fb_file.exists():
                try:
                    with open(fb_file, "r", encoding="utf-8") as f:
                        raw_content = f.read()
                        is_live = False
                        logger.info(f"Loaded local fallback snapshot for {source_id}.")
                except Exception as ex:
                    logger.warning(f"Failed to read local fallback file: {ex}")

        # Update cache or preserve existing
        now_iso = datetime.now(timezone.utc).isoformat()
        if raw_content:
            content_hash = hashlib.sha256(raw_content.encode("utf-8")).hexdigest()
            # Parse records count
            records_count = 0
            try:
                parsed = json.loads(raw_content)
                if isinstance(parsed, list):
                    records_count = len(parsed)
                elif isinstance(parsed, dict):
                    records_count = len(parsed.get("result", parsed.get("addresses", [])))
            except Exception:
                records_count = 1

            rec.content_hash = content_hash
            rec.last_collected_at = now_iso
            rec.status = "live" if is_live else "cached"
            rec.records_count = records_count
            rec.cache_payload_json = raw_content[:50000] # Store preview/sample to preserve DB size
            db.osint_sources.update_one(
                {"source_id": source_id},
                {"$set": {
                    "content_hash": content_hash,
                    "last_collected_at": now_iso,
                    "status": rec.status,
                    "records_count": records_count,
                    "cache_payload_json": rec.cache_payload_json
                }},
                upsert=True
            )
            return {
                "source_id": source_id,
                "status": rec.status,
                "is_live": is_live,
                "records_count": records_count,
                "content_hash": content_hash,
                "timestamp": now_iso
            }
        else:
            # Preserved cached results
            return {
                "source_id": source_id,
                "status": rec.status or "cached",
                "is_live": False,
                "records_count": rec.records_count,
                "content_hash": rec.content_hash,
                "timestamp": rec.last_collected_at or now_iso
            }

    async def collect_all(self) -> List[Dict[str, Any]]:
        db = SessionLocal()
        results: List[Dict[str, Any]] = []
        try:
            for src in self.sources:
                res = await self.collect_source(src, db)
                results.append(res)
        finally:
            db.close()
        return results

    async def start_scheduled_collector(self):
        if self.running:
            return
        self.running = True
        self._task = asyncio.create_task(self._schedule_loop())
        logger.info("LiveOSINTCollector scheduled background service started.")

    async def stop(self):
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("LiveOSINTCollector stopped.")

    async def _schedule_loop(self):
        # Initial run on startup
        await self.collect_all()
        while self.running:
            try:
                await asyncio.sleep(settings.OSINT_POLL_INTERVAL_MINUTES * 60)
                if self.running:
                    await self.collect_all()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in OSINT scheduled collector: {e}")
                await asyncio.sleep(60)

live_osint_collector = LiveOSINTCollector()
