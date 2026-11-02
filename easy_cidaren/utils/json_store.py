"""Write JSON without truncating the existing file on failure."""

import json
import os
import tempfile
from pathlib import Path


def write_json(path, value, *, indent = None):
    path = Path(path)
    descriptor, temporary = tempfile.mkstemp(prefix = f'.{path.name}.', dir = path.parent)
    try:
        with os.fdopen(descriptor, 'w', encoding = 'utf-8') as stream:
            json.dump(value, stream, ensure_ascii = False, indent = indent)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
