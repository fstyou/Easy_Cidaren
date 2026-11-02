"""Paths shared by the source checkout and its runtime data."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve( ).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
ASSETS_DIR = PROJECT_ROOT / "assets"
MODEL_DIR = DATA_DIR / "models" / "en_core_web_sm"
RUNTIME_DIR = PROJECT_ROOT / "runtime"
LOG_DIR = RUNTIME_DIR / "logs"
CAPTURE_DATA_DIR = RUNTIME_DIR / "token_capture"
