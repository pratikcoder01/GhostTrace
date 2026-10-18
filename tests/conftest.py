import sys
import types
from pathlib import Path

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Alias 'backend.app' -> 'app'
if "backend" not in sys.modules:
    import app
    b = types.ModuleType("backend")
    b.app = app
    sys.modules["backend"] = b
    sys.modules["backend.app"] = app
