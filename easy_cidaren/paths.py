"""Paths for bundled resources and writable user data."""

import os
import shutil
import sys
import tempfile
from pathlib import Path


def user_data_root(platform: str, home: Path, environ: dict) -> Path:
    if platform == 'win32':
        base = Path(environ.get('LOCALAPPDATA') or home / 'AppData' / 'Local')
    elif platform == 'darwin':
        base = home / 'Library' / 'Application Support'
    else:
        configured = Path(environ.get('XDG_DATA_HOME') or home / '.local' / 'share')
        base = configured if configured.is_absolute( ) else home / '.local' / 'share'
    return base / 'EasyCidaren'


def initialize_seed_data(source: Path, destination: Path):
    """Copy shipped dictionaries only on first use; never replace user data."""
    destination.mkdir(parents = True, exist_ok = True)
    for name in ('answer_lib.json', 'word_pool.json'):
        seed = source / name
        if not seed.is_file( ):
            continue
        target = destination / name
        if target.exists( ):
            continue
        temporary = None
        try:
            with seed.open('rb') as input_file, tempfile.NamedTemporaryFile(dir = destination,
                                                                            delete = False) as output:
                temporary = Path(output.name)
                shutil.copyfileobj(input_file, output.file)
            try:
                os.link(temporary, target)
            except FileExistsError:
                pass
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok = True)


PROJECT_ROOT = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve( ).parent.parent))
ASSETS_DIR = PROJECT_ROOT / 'assets'
MODEL_DIR = PROJECT_ROOT / 'data' / 'models' / 'en_core_web_sm'
if getattr(sys, 'frozen', False):
    writable_root = user_data_root(sys.platform, Path.home( ), dict(os.environ))
    DATA_DIR = writable_root / 'data'
    RUNTIME_DIR = writable_root / 'runtime'
    initialize_seed_data(PROJECT_ROOT / 'data', DATA_DIR)
else:
    DATA_DIR = PROJECT_ROOT / 'data'
    RUNTIME_DIR = PROJECT_ROOT / 'runtime'
LOG_DIR = RUNTIME_DIR / "logs"
CAPTURE_DATA_DIR = RUNTIME_DIR / "token_capture"
