from tests.module_loader import load_module

import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


class WordListTests(unittest.TestCase):
    def test_word_pool_is_written_to_data_directory(self):
        path = Path(__file__).resolve( ).parents[1] / 'easy_cidaren' / 'core' / 'word_list.py'
        with tempfile.TemporaryDirectory( ) as directory:
            data_dir = Path(directory) / 'data'
            data_dir.mkdir( )
            info = types.SimpleNamespace(
                    word_dict = {'原有': 'existing'}, self_learn_pool = True,
                    get_word_list_result = {'data': {'word_list': [{'word': 'word', 'word_zh': '含义'}]}},
            )
            with patch.dict(sys.modules, {'easy_cidaren.security.decode': types.SimpleNamespace(debase64 = None)}):
                module = load_module('test_word_list_module', path)
                with patch.object(module, 'DATA_DIR', data_dir):
                    module.handle_word_result(info)
            saved = json.loads((data_dir / 'word_pool.json').read_text(encoding = 'utf-8'))
            self.assertEqual(saved, {'原有': 'existing', '含义': 'word'})
            self.assertEqual(info.word_list, ['word'])

    def test_encoded_word_response_is_decoded_only_once(self):
        from easy_cidaren.core.word_list import decode_word_result
        decoded = {'word_list': [], 'exist_little_task': 2}
        info = types.SimpleNamespace(get_word_list_result = {'data': 'encoded', 'jv': '2_test'})
        with patch('easy_cidaren.core.word_list.debase64', Mock(return_value = decoded)) as decode:
            self.assertIs(decode_word_result(info), decoded)
            self.assertIs(decode_word_result(info), decoded)
            decode.assert_called_once_with('encoded', '2_test')

    def test_invalid_word_response_is_reported(self):
        from easy_cidaren.core.word_list import decode_word_result
        info = types.SimpleNamespace(get_word_list_result = {'data': {'word_list': None}})
        with self.assertRaisesRegex(ValueError, '有效词表'):
            decode_word_result(info)


if __name__ == '__main__':
    unittest.main( )
