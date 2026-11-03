import tempfile
import unittest
from pathlib import Path

from easy_cidaren.token_capture.token_store import load_token


class TokenStoreTests(unittest.TestCase):
    def test_loads_saved_token_when_present(self):
        with tempfile.TemporaryDirectory( ) as directory:
            self.assertEqual(load_token(directory), '')
            (Path(directory) / 'last_token.txt').write_text(' token-value\n', encoding = 'utf-8')
            self.assertEqual(load_token(directory), 'token-value')


if __name__ == '__main__':
    unittest.main( )
