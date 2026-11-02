"""Read the most recently captured token."""

from pathlib import Path

from easy_cidaren.paths import CAPTURE_DATA_DIR

SAVED_TOKEN_FILE = 'last_token.txt'


def load_token(directory = CAPTURE_DATA_DIR):
    """Read the most recently saved token."""
    try:
        return (Path(directory) / SAVED_TOKEN_FILE).read_text(encoding = 'utf-8').strip( )
    except (OSError, UnicodeError):
        return ''
