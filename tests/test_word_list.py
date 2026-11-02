import importlib.util
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch


class WordListTests(unittest.TestCase):
    def test_word_pool_is_written_to_data_directory(self):
        path = Path(__file__).resolve( ).parents[1] / 'easy_cidaren' / 'core' / 'word_list.py'
        with tempfile.TemporaryDirectory( ) as directory:
            data_dir = Path(directory) / 'data'
            data_dir.mkdir( )
            info = types.SimpleNamespace(
                    word_dict = {'原有': 'existing'}, _self_learn_pool = True,
                    get_word_list_result = {'data': {'word_list': [{'word': 'word', 'word_zh': '含义'}]}},
            )
            with patch.dict(sys.modules, {'easy_cidaren.security.decode': types.SimpleNamespace(debase64 = None)}):
                spec = importlib.util.spec_from_file_location('test_word_list_module', path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                with patch.object(module, 'DATA_DIR', data_dir):
                    module.handle_word_result(info)
            saved = json.loads((data_dir / 'word_pool.json').read_text(encoding = 'utf-8'))
            self.assertEqual(saved, {'原有': 'existing', '含义': 'word'})
            self.assertEqual(info.word_list, ['word'])


if __name__ == '__main__':
    unittest.main( )
