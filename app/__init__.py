import sys
import types
from pathlib import Path

# Ensure 'backend' namespace is resolvable whether running as `uvicorn app.main:app` or `uvicorn backend.app.main:app`
_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

if "backend" not in sys.modules:
    try:
        import backend  # already resolves if ghosttrace root is on sys.path
    except ImportError:
        _b = types.ModuleType("backend")
        _b.app = sys.modules[__name__]
        sys.modules["backend"] = _b
        sys.modules["backend.app"] = sys.modules[__name__]
