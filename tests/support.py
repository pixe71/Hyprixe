"""Source-layout helpers shared by fixtures; installed HOME paths are unchanged."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from source_layout import configure_imports, source_path, shell_bytes
configure_imports()
