import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from tests import PROJECT_ROOT
from tests.module_loader import load_module


class CaptureAddonTests(unittest.TestCase):
    def test_only_target_token_is_written_without_capture_log(self):
        path = PROJECT_ROOT / 'easy_cidaren' / 'token_capture' / 'addon.py'
        http = types.SimpleNamespace(HTTPFlow = object)
        with tempfile.TemporaryDirectory( ) as directory, \
                patch.dict(os.environ, {'EASY_CIDAREN_TOKEN_FILE': str(Path(directory) / 'last_token.txt')}), \
                patch.dict(sys.modules, {'mitmproxy': types.SimpleNamespace(http = http)}):
            module = load_module('test_capture_addon_module', path)
            catcher = module.TokenCatcher( )
            catcher.response(types.SimpleNamespace(request = types.SimpleNamespace(
                    host = 'example.com', headers = {'UserToken': 'other'})))
            catcher.response(types.SimpleNamespace(request = types.SimpleNamespace(
                    host = 'app.vocabgo.com', headers = {})))
            self.assertEqual(list(Path(directory).iterdir( )), [])
            catcher.response(types.SimpleNamespace(request = types.SimpleNamespace(
                    host = 'app.vocabgo.com', headers = {'UserToken': 'test-token'})))
            self.assertEqual((Path(directory) / 'last_token.txt').read_text(encoding = 'utf-8'), 'test-token')
            self.assertEqual([p.name for p in Path(directory).iterdir( )], ['last_token.txt'])
            with patch.object(os, 'replace', side_effect = OSError('failed')):
                with self.assertRaises(OSError):
                    catcher.response(types.SimpleNamespace(request = types.SimpleNamespace(
                            host = 'app.vocabgo.com', headers = {'UserToken': 'new-token'})))
            self.assertEqual((Path(directory) / 'last_token.txt').read_text(encoding = 'utf-8'), 'test-token')
            self.assertEqual([p.name for p in Path(directory).iterdir( )], ['last_token.txt'])


if __name__ == '__main__':
    unittest.main( )
