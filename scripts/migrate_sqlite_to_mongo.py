#!/usr/bin/env python3
"""
GhostTrace SQLite to MongoDB Atlas Migration Script
===================================================
Migrates existing SQLite database records into MongoDB Atlas collections.
Preserves existing SQLite database file without deletion or corruption.
Features idempotent upserts, dry-run mode, relationship preservation, and audit logging.
"""

import os
import sys
import json
import sqlite3
import argparse
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple

# Ensure backend can be imported
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
ROOT_DIR = BACKEND_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from backend.app.config import settings
from backend.app.mongodb import MongoDBManager, get_masked_uri

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("SQLiteToMongoMigrator")

TABLE_COLLECTION_MAP = {
    "cases": "cases",
    "transactions": "transactions",
    "evidence": "evidence",
    "tracechain_blocks": "tracechain_blocks",
    "block_cursors": "block_cursors",
    "raw_blockchain_events": "raw_blockchain_events",
    "osint_sources": "osint_sources",
    "ml_models": "ml_models"
}

def transform_row(table_name: str, row: Dict[str, Any]) -> Dict[str, Any]:
    """Transforms a SQLite row dictionary into the MongoDB document schema."""
    doc = dict(row)

    if table_name == "cases":
        case_id = doc.get("case_id")
        doc["_id"] = case_id
        # Convert seed_addresses_json into native list
        if "seed_addresses_json" in doc and doc["seed_addresses_json"]:
            try:
                doc["seed_addresses"] = json.loads(doc["seed_addresses_json"])
            except Exception:
                doc["seed_addresses"] = []
        else:
            doc["seed_addresses"] = []
        # Convert summary_json into native dict
        if "summary_json" in doc and doc["summary_json"]:
            try:
                doc["summary"] = json.loads(doc["summary_json"])
            except Exception:
                doc["summary"] = None
        else:
            doc["summary"] = None

    elif table_name == "transactions":
        case_id = doc.get("case_id", "")
        tx_id = doc.get("tx_id", "")
        doc["_id"] = f"{case_id}:{tx_id}"
        # Convert extra_metadata_json
        if "extra_metadata_json" in doc and doc["extra_metadata_json"]:
            try:
                doc["extra_metadata"] = json.loads(doc["extra_metadata_json"])
            except Exception:
                doc["extra_metadata"] = {}
        else:
            doc["extra_metadata"] = {}
        # Convert reorg boolean
        if "is_reorg_removed" in doc:
            doc["is_reorg_removed"] = bool(doc["is_reorg_removed"])

    elif table_name == "evidence":
        case_id = doc.get("case_id", "")
        evidence_id = doc.get("evidence_id", "")
        doc["_id"] = f"{case_id}:{evidence_id}"

    elif table_name == "tracechain_blocks":
        b_idx = int(doc.get("block_index", 0))
        doc["_id"] = b_idx
        doc["block_index"] = b_idx
        if "payload_json" in doc and doc["payload_json"]:
            try:
                doc["payload"] = json.loads(doc["payload_json"])
            except Exception:
                doc["payload"] = {}
        else:
            doc["payload"] = {}

    elif table_name == "block_cursors":
        network = doc.get("network", "")
        doc["_id"] = network

    elif table_name == "raw_blockchain_events":
        event_id = doc.get("event_id", "")
        doc["_id"] = event_id
        if "raw_payload_json" in doc and doc["raw_payload_json"]:
            try:
                doc["raw_payload"] = json.loads(doc["raw_payload_json"])
            except Exception:
                doc["raw_payload"] = {}
        else:
            doc["raw_payload"] = {}

    elif table_name == "osint_sources":
        source_id = doc.get("source_id", "")
        doc["_id"] = source_id
        if "cache_payload_json" in doc and doc["cache_payload_json"]:
            try:
                doc["cache_payload"] = json.loads(doc["cache_payload_json"])
            except Exception:
                doc["cache_payload"] = None
        else:
            doc["cache_payload"] = None

    elif table_name == "ml_models":
        model_id = doc.get("model_id", "")
        doc["_id"] = model_id
        if "metrics_json" in doc and doc["metrics_json"]:
            try:
                doc["metrics"] = json.loads(doc["metrics_json"])
            except Exception:
                doc["metrics"] = {}
        if "parameters_json" in doc and doc["parameters_json"]:
            try:
                doc["parameters"] = json.loads(doc["parameters_json"])
            except Exception:
                doc["parameters"] = {}

    return doc

def migrate_sqlite_to_mongodb(
    sqlite_path: Path,
    mongodb_uri: str,
    mongodb_database: str,
    dry_run: bool = False,
    batch_size: int = 500
) -> Dict[str, Any]:
    """Executes the data migration and returns an audit verification summary."""
    if not sqlite_path.exists():
        raise FileNotFoundError(f"SQLite database file not found at: {sqlite_path}")

    logger.info(f"Source SQLite file: {sqlite_path} ({round(sqlite_path.stat().st_size / 1024, 2)} KB)")
    logger.info(f"Target MongoDB: {get_masked_uri(mongodb_uri)} | Database: {mongodb_database}")
    logger.info(f"Execution Mode: {'DRY-RUN (No writes)' if dry_run else 'LIVE MIGRATION'}")

    # Initialize MongoDB
    mongo = MongoDBManager()
    mongo.connect(uri=mongodb_uri, database=mongodb_database)
    db = mongo.get_database()

    # Open SQLite read-only
    conn = sqlite3.connect(f"file:{sqlite_path.resolve()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    report: Dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sqlite_path": str(sqlite_path),
        "target_database": mongodb_database,
        "dry_run": dry_run,
        "collections": {}
    }

    # Discover tables
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    existing_tables = [r[0] for r in cur.fetchall()]

    for table in existing_tables:
        if table not in TABLE_COLLECTION_MAP:
            logger.info(f"Skipping unmapped SQLite table: {table}")
            continue

        collection_name = TABLE_COLLECTION_MAP[table]
        collection = db[collection_name]

        cur.execute(f"SELECT COUNT(*) FROM {table}")
        source_count = cur.fetchone()[0]

        logger.info(f"\nProcessing table '{table}' -> collection '{collection_name}' (Source rows: {source_count})")

        stats = {
            "source_count": source_count,
            "migrated_or_matched": 0,
            "existing_before": collection.count_documents({}),
            "skipped_or_unchanged": 0,
            "errors": 0
        }

        if source_count == 0:
            stats["destination_count_after"] = stats["existing_before"]
            report["collections"][table] = stats
            continue

        cur.execute(f"SELECT * FROM {table}")
        batch = []
        while True:
            rows = cur.fetchmany(batch_size)
            if not rows:
                break

            for r in rows:
                row_dict = dict(r)
                doc = transform_row(table, row_dict)
                doc_id = doc["_id"]

                try:
                    if dry_run:
                        # Check existence in target
                        existing = collection.find_one({"_id": doc_id})
                        if existing:
                            stats["skipped_or_unchanged"] += 1
                        else:
                            stats["migrated_or_matched"] += 1
                    else:
                        # Idempotent upsert
                        res = collection.update_one({"_id": doc_id}, {"$set": doc}, upsert=True)
                        if res.upserted_id or res.modified_count > 0:
                            stats["migrated_or_matched"] += 1
                        else:
                            stats["skipped_or_unchanged"] += 1
                except Exception as ex:
                    logger.error(f"Error migrating row {doc_id} in {table}: {ex}")
                    stats["errors"] += 1

        stats["destination_count_after"] = collection.count_documents({})
        report["collections"][table] = stats
        logger.info(
            f"Table '{table}' finished: {stats['migrated_or_matched']} migrated, "
            f"{stats['skipped_or_unchanged']} unchanged, {stats['errors']} errors. "
            f"Total target docs: {stats['destination_count_after']}"
        )

    conn.close()
    return report

def main():
    parser = argparse.ArgumentParser(description="GhostTrace SQLite to MongoDB Atlas Migration Tool")
    parser.add_argument("--sqlite-path", type=str, default=str(settings.BASE_DIR / "data" / "ghosttrace.db"), help="Path to SQLite database")
    parser.add_argument("--mongodb-uri", type=str, default=settings.MONGODB_URI, help="MongoDB connection URI")
    parser.add_argument("--database", type=str, default=settings.MONGODB_DATABASE, help="MongoDB target database name")
    parser.add_argument("--dry-run", action="store_true", help="Perform a dry-run analysis without writing to MongoDB")
    parser.add_argument("--batch-size", type=int, default=500, help="Batch size for reading and inserting records")

    args = parser.parse_args()
    report = migrate_sqlite_to_mongodb(
        sqlite_path=Path(args.sqlite_path),
        mongodb_uri=args.mongodb_uri,
        mongodb_database=args.database,
        dry_run=args.dry_run,
        batch_size=args.batch_size
    )

    print("\n" + "=" * 65)
    print("  GHOSTTRACE MIGRATION AUDIT REPORT")
    print("=" * 65)
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
