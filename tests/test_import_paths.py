import subprocess
import sys
import unittest
from pathlib import Path


class ImportPathTests(unittest.TestCase):
    def test_source_root_does_not_shadow_standard_logging(self):
        root = Path(__file__).resolve( ).parents[1]
        code = (
            'import sys; '
            f'sys.path.insert(0, {str(root / "easy_cidaren")!r}); '
            'import logging; '
            'assert hasattr(logging, "Filter"); '
            'import easy_cidaren.core.public_info'
        )
        subprocess.run([sys.executable, '-c', code], cwd = root, check = True)
