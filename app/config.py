import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel

# Base directory for backend
BASE_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BASE_DIR.parent

# Load .env if present
load_dotenv(BASE_DIR / ".env")
load_dotenv(ROOT_DIR / ".env")


class Settings(BaseModel):
    PROJECT_NAME: str = "GhostTrace Forensic Intelligence Platform"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    
    # Paths
    BASE_DIR: Path = BASE_DIR
    DATA_DIR: Path = BASE_DIR / "data"
    MODELS_DIR: Path = BASE_DIR / "models"
    REPORTS_DIR: Path = BASE_DIR / "reports"
    
    # Database Settings
    MONGODB_URI: str = os.getenv("MONGODB_URI", "")
    MONGODB_DATABASE: str = os.getenv("MONGODB_DATABASE", "ghosttrace")
    MONGODB_MAX_POOL_SIZE: int = int(os.getenv("MONGODB_MAX_POOL_SIZE", "50"))
    MONGODB_MIN_POOL_SIZE: int = int(os.getenv("MONGODB_MIN_POOL_SIZE", "5"))
    MONGODB_TIMEOUT_MS: int = int(os.getenv("MONGODB_TIMEOUT_MS", "5000"))
    
    # Legacy Database (for SQLite migration script only)
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'data' / 'ghosttrace.db'}")
    
    # TraceChain Settings
    TRACECHAIN_DIFFICULTY: int = int(os.getenv("TRACECHAIN_DIFFICULTY", "2"))
    
    # External Adapters (Optional)
    ETHERSCAN_API_KEY: str = os.getenv("ETHERSCAN_API_KEY", "")
    ETHERSCAN_BASE_URL: str = os.getenv("ETHERSCAN_BASE_URL", "https://api.etherscan.io/api")
    
    # Alchemy Real-Time Ingestion
    ALCHEMY_API_KEY: str = os.getenv("ALCHEMY_API_KEY", "")
    ALCHEMY_WS_URL: str = os.getenv("ALCHEMY_WS_URL", "")
    ALCHEMY_HTTP_URL: str = os.getenv("ALCHEMY_HTTP_URL", "")
    ETHEREUM_NETWORK: str = os.getenv("ETHEREUM_NETWORK", "mainnet")
    ETHEREUM_CHAIN_ID: int = int(os.getenv("ETHEREUM_CHAIN_ID", "1"))
    
    # Live Ingestion & Simulator Settings
    LIVE_INGESTION_ENABLED: bool = os.getenv("LIVE_INGESTION_ENABLED", "true").lower() in ("true", "1", "yes")
    LIVE_SIMULATOR_ENABLED: bool = os.getenv("LIVE_SIMULATOR_ENABLED", "true").lower() in ("true", "1", "yes")
    BACKFILL_BLOCK_LIMIT: int = int(os.getenv("BACKFILL_BLOCK_LIMIT", "20"))
    OSINT_POLL_INTERVAL_MINUTES: int = int(os.getenv("OSINT_POLL_INTERVAL_MINUTES", "60"))
    WS_HEARTBEAT_INTERVAL: float = float(os.getenv("WS_HEARTBEAT_INTERVAL", "15.0"))
    
    # ML settings
    DEFAULT_RANDOM_STATE: int = 42
    ML_ACTIVE_THRESHOLD: float = float(os.getenv("ML_ACTIVE_THRESHOLD", "0.42"))
    ELLIPTIC_DATA_DIR: Path = BASE_DIR / "data" / "elliptic" / "elliptic_bitcoin_dataset"
    
    # Datasets
    SYNTHETIC_ATTACK_FILE: Path = BASE_DIR / "data" / "synthetic_attack.json"
    CRYPTOSCAMDB_FILE: Path = BASE_DIR / "data" / "cryptoscamdb_snapshot.json"
    PEGASUS_CSV_FILE: Path = BASE_DIR / "data" / "pegasus" / "synthetic_pegasus_dataset.csv"

settings = Settings()

# Ensure required directories exist
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
settings.MODELS_DIR.mkdir(parents=True, exist_ok=True)
settings.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
