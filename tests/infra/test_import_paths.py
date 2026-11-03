import subprocess
import sys
import unittest

from tests import PROJECT_ROOT


class ImportPathTests(unittest.TestCase):
    def test_source_root_does_not_shadow_standard_logging(self):
        root = PROJECT_ROOT
        code = (
            'import sys; '
            f'sys.path.insert(0, {str(root / "easy_cidaren")!r}); '
            'import logging; '
            'assert hasattr(logging, "Filter"); '
            'import easy_cidaren.core.public_info'
        )
        subprocess.run([sys.executable, '-c', code], cwd = root, check = True)
