import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from easy_cidaren.utils.json_store import write_json


class JsonStoreTests(unittest.TestCase):
    def test_failed_replace_preserves_existing_file(self):
        with tempfile.TemporaryDirectory( ) as directory:
            path = Path(directory) / 'data.json'
            write_json(path, {'原有': 1})
            with patch('easy_cidaren.utils.json_store.os.replace', side_effect = OSError('failed')):
                with self.assertRaises(OSError):
                    write_json(path, {'新值': 2})
            self.assertEqual(json.loads(path.read_text(encoding = 'utf-8')), {'原有': 1})
            self.assertEqual(list(Path(directory).iterdir( )), [path])


if __name__ == '__main__':
    unittest.main( )
