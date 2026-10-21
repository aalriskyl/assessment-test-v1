import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
if sys.prefix == sys.base_prefix:
    sys.path.insert(0, str(ROOT / ".deps"))
