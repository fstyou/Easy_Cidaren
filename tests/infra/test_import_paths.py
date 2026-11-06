import runpy
import subprocess
import sys
import unittest
from types import ModuleType
from unittest.mock import patch

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


class InternalCaptureEntryTests(unittest.TestCase):
    def test_internal_capture_has_streams_without_replacing_existing_ones(self):
        original = {name: getattr(sys, name) for name in ('stdin', 'stdout', 'stderr')}
        for windowed in (False, True):
            with self.subTest(windowed = windowed):
                streams = dict.fromkeys(original) if windowed else original
                module = ModuleType('mitmproxy.tools.main')
                calls = []
                
                def mitmdump( ):
                    calls.append(sys.argv[1:])
                    for name in original:
                        stream = getattr(sys, name)
                        self.assertIsNotNone(stream)
                        self.assertIsInstance(stream.isatty( ), bool)
                        if not windowed:
                            self.assertIs(stream, original[name])
                    if windowed:
                        self.assertEqual(sys.stdin.read( ), '')
                        sys.stdout.write('capture output')
                        sys.stderr.write('capture error')
                
                module.mitmdump = mitmdump
                with patch.dict(sys.modules, {'mitmproxy.tools.main': module}), \
                        patch.object(sys, 'argv', ['main.py', '--internal-mitmdump', '--version']), \
                        patch.multiple(sys, **streams):
                    try:
                        runpy.run_path(str(PROJECT_ROOT / 'main.py'), run_name = '__main__')
                    finally:
                        if windowed:
                            for name in original:
                                temporary_stream = getattr(sys, name)
                                if temporary_stream is not None:
                                    temporary_stream.close( )
                self.assertEqual(calls, [['--version']])
