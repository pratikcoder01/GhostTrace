import os
import re
import time
import logging
from typing import Optional, Dict, Any, Generator
import pymongo
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError, PyMongoError
import mongomock

from backend.app.config import settings

logger = logging.getLogger(__name__)

def get_masked_uri(uri: Optional[str]) -> str:
    """Masks credentials in MongoDB connection string for safe logging and diagnostics."""
    if not uri:
        return "Not Configured"
    if uri == "mongomock":
        return "mongomock://in-memory"
    return re.sub(r"://([^:]+):([^@]+)@", r"://\1:***@", uri)

class MongoDBManager:
    """
    Centralized MongoDB Connection Manager for GhostTrace.
    Supports real MongoDB Atlas clusters via PyMongo / Motor and
    in-memory mongomock for safe, isolated offline automated testing.
    """
    def __init__(self):
        self.client: Optional[Any] = None
        self.async_client: Optional[Any] = None
        self.db_name: str = settings.MONGODB_DATABASE
        self._is_mock: bool = False
        self._connected: bool = False

    def connect(self, uri: Optional[str] = None, database: Optional[str] = None, force_mock: bool = False):
        """Initializes client connection and verifies connectivity via ping."""
        target_uri = uri if uri is not None else settings.MONGODB_URI
        self.db_name = database if database is not None else settings.MONGODB_DATABASE

        # Determine whether to use real connection or mongomock
        if force_mock or not target_uri or target_uri.strip().lower() in ("mock", "mongomock", "test", ""):
            logger.info("Initializing in-memory mongomock connection for GhostTrace testing/offline execution.")
            self.client = mongomock.MongoClient()
            self._is_mock = True
            self._connected = True
            try:
                import motor.motor_asyncio
                # Motor wrapper or mock fallback
                self.async_client = None
            except Exception:
                self.async_client = None
            self.create_indexes()
            return

        masked = get_masked_uri(target_uri)
        logger.info(f"Connecting to MongoDB Atlas endpoint: {masked} | Database: {self.db_name}")

        try:
            self.client = MongoClient(
                target_uri,
                maxPoolSize=settings.MONGODB_MAX_POOL_SIZE,
                minPoolSize=settings.MONGODB_MIN_POOL_SIZE,
                serverSelectionTimeoutMS=settings.MONGODB_TIMEOUT_MS,
                connectTimeoutMS=settings.MONGODB_TIMEOUT_MS,
                socketTimeoutMS=settings.MONGODB_TIMEOUT_MS,
                appname="GhostTraceBackend"
            )
            # Verify immediate connection
            self.client.admin.command("ping")
            self._connected = True
            self._is_mock = False
            logger.info("MongoDB Atlas cluster ping verified successfully.")

            # Initialize Motor async client if available
            try:
                import motor.motor_asyncio
                self.async_client = motor.motor_asyncio.AsyncIOMotorClient(
                    target_uri,
                    maxPoolSize=settings.MONGODB_MAX_POOL_SIZE,
                    minPoolSize=settings.MONGODB_MIN_POOL_SIZE,
                    serverSelectionTimeoutMS=settings.MONGODB_TIMEOUT_MS,
                    connectTimeoutMS=settings.MONGODB_TIMEOUT_MS
                )
            except Exception as e:
                logger.warning(f"Motor async client initialization notice: {e}")

            self.create_indexes()

        except (ConnectionFailure, ServerSelectionTimeoutError) as ce:
            logger.error(f"MongoDB connection failed to {masked}: {ce}")
            self._connected = False
            raise RuntimeError(f"Unable to connect to MongoDB at {masked}: {str(ce)}")

    def disconnect(self):
        """Closes all database connections gracefully."""
        if self.client:
            try:
                self.client.close()
            except Exception:
                pass
            self.client = None
        if self.async_client:
            try:
                self.async_client.close()
            except Exception:
                pass
            self.async_client = None
        self._connected = False
        logger.info("MongoDB connections closed cleanly.")

    def get_database(self, name: Optional[str] = None):
        """Returns the synchronized Database handle, auto-connecting if needed."""
        if self.client is None:
            self.connect()
        target_name = name or self.db_name
        return self.client[target_name]

    def get_async_database(self, name: Optional[str] = None):
        """Returns the asynchronous Motor database handle if available."""
        if self.async_client is None:
            if self._is_mock or not settings.MONGODB_URI:
                return None
            self.connect()
        target_name = name or self.db_name
        return self.async_client[target_name] if self.async_client else None

    def ping(self) -> Dict[str, Any]:
        """Performs a live database health check."""
        if not self.client:
            return {
                "status": "disconnected",
                "connected": False,
                "database": self.db_name,
                "is_mock": False,
                "masked_uri": get_masked_uri(settings.MONGODB_URI)
            }
        start = time.perf_counter()
        try:
            db = self.get_database()
            db.command("ping")
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            return {
                "status": "connected",
                "connected": True,
                "database": self.db_name,
                "latency_ms": latency_ms,
                "is_mock": self._is_mock,
                "masked_uri": get_masked_uri("mongomock" if self._is_mock else settings.MONGODB_URI)
            }
        except Exception as e:
            return {
                "status": "error",
                "connected": False,
                "database": self.db_name,
                "error": str(e),
                "is_mock": self._is_mock,
                "masked_uri": get_masked_uri(settings.MONGODB_URI)
            }

    def create_indexes(self):
        """Ensures all necessary performance and uniqueness constraints exist in collections."""
        try:
            db = self.get_database()
            # 1. Cases: unique case_id, created_at descending
            db.cases.create_index([("case_id", pymongo.ASCENDING)], unique=True)
            db.cases.create_index([("created_at", pymongo.DESCENDING)])
            db.cases.create_index([("network", pymongo.ASCENDING)])

            # 2. Transactions: compound uniqueness on (case_id, tx_id), fast timeline index
            db.transactions.create_index(
                [("case_id", pymongo.ASCENDING), ("tx_id", pymongo.ASCENDING)],
                unique=True
            )
            db.transactions.create_index([("case_id", pymongo.ASCENDING), ("timestamp", pymongo.ASCENDING)])
            db.transactions.create_index([("from_address", pymongo.ASCENDING)])
            db.transactions.create_index([("to_address", pymongo.ASCENDING)])
            db.transactions.create_index([("tx_hash", pymongo.ASCENDING)])

            # 3. Evidence: compound uniqueness on (case_id, evidence_id)
            db.evidence.create_index(
                [("case_id", pymongo.ASCENDING), ("evidence_id", pymongo.ASCENDING)],
                unique=True
            )
            db.evidence.create_index([("case_id", pymongo.ASCENDING), ("indicator_value", pymongo.ASCENDING)])

            # 4. TraceChain Blocks: unique block_index and block_hash
            db.tracechain_blocks.create_index([("block_index", pymongo.ASCENDING)], unique=True)
            db.tracechain_blocks.create_index([("block_hash", pymongo.ASCENDING)], unique=True)
            db.tracechain_blocks.create_index([("case_id", pymongo.ASCENDING)])

            # 5. Ingestion Checkpoints (Block Cursors): unique per network
            db.block_cursors.create_index([("network", pymongo.ASCENDING)], unique=True)

            # 6. Raw Blockchain Events: unique event_id
            db.raw_blockchain_events.create_index([("event_id", pymongo.ASCENDING)], unique=True)
            db.raw_blockchain_events.create_index([("network", pymongo.ASCENDING), ("block_number", pymongo.DESCENDING)])
            db.raw_blockchain_events.create_index([("tx_hash", pymongo.ASCENDING)])

            # 7. OSINT Sources
            db.osint_sources.create_index([("source_id", pymongo.ASCENDING)], unique=True)

            logger.info("MongoDB collection indexes validated and initialized.")
        except Exception as e:
            logger.warning(f"Index creation notice: {e}")

# Global singleton manager
mongo_manager = MongoDBManager()

def get_database(name: Optional[str] = None):
    """Convenience getter for current MongoDB database."""
    return mongo_manager.get_database(name)

def get_async_database(name: Optional[str] = None):
    """Convenience getter for async MongoDB database."""
    return mongo_manager.get_async_database(name)

def connect_mongodb(uri: Optional[str] = None, database: Optional[str] = None, force_mock: bool = False):
    """Initializes global MongoDB connection."""
    mongo_manager.connect(uri=uri, database=database, force_mock=force_mock)

def close_mongodb():
    """Closes global MongoDB connection."""
    mongo_manager.disconnect()

def ping_mongodb() -> Dict[str, Any]:
    """Runs health check ping."""
    return mongo_manager.ping()

def get_db() -> Generator[Any, None, None]:
    """
    FastAPI dependency that provides the active MongoDB database instance.
    Replaces legacy SQLite SQLAlchemy Session generator.
    """
    yield mongo_manager.get_database()
