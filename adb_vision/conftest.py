"""pytest configuration — add adb_vision/ to sys.path so local imports work."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
