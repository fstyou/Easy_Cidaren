"""Find executables installed alongside the Python interpreter."""
import os
import shutil
import sys
from pathlib import Path


def find_mitmdump():
    name = "mitmdump.exe" if os.name == "nt" else "mitmdump"
    candidate = Path(sys.executable).parent / name
    if candidate.is_file():
        return str(candidate)
    return shutil.which("mitmdump")
