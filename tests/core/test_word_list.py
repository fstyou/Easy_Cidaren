import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from easy_cidaren.core import word_list
from easy_cidaren.core.settings import Settings


class WordListTests(unittest.TestCase):
    def test_self_built_words_are_grouped_by_their_actual_unit(self):
        info = SimpleNamespace(course_id = 'course', get_word_list_result = {'word_list': [
            {'word': 'one', 'list_id': 'unit-a'}, {'word': 'two', 'list_id': 'unit-b'},
            {'word': 'three', 'list_id': 'unit-a'},
        ]})
        self.assertEqual(word_list.query_word_unit(info), {'course:unit-a': ['one', 'three'], 'course:unit-b': ['two']})
    
    def test_word_pool_is_written_to_data_directory(self):
        with tempfile.TemporaryDirectory( ) as directory:
            data_dir = Path(directory)
            info = SimpleNamespace(
                    word_dict = {'原有': 'existing'}, settings = Settings( ),
                    get_word_list_result = {'data': {'word_list': [{'word': 'word', 'word_zh': '含义'}]}},
            )
            with patch('easy_cidaren.core.word_list.DATA_DIR', data_dir):
                word_list.handle_word_result(info)
            saved = json.loads((data_dir / 'word_pool.json').read_text(encoding = 'utf-8'))
            self.assertEqual(saved, {'原有': 'existing', '含义': 'word'})
            self.assertEqual(info.word_list, ['word'])
    
    def test_encoded_word_response_is_decoded_only_once(self):
        decoded = {'word_list': [], 'exist_little_task': 2}
        info = SimpleNamespace(get_word_list_result = {'data': 'encoded', 'jv': '2_test'})
        with patch('easy_cidaren.core.word_list.debase64', return_value = decoded) as decode:
            self.assertIs(word_list.decode_word_result(info), decoded)
            self.assertIs(word_list.decode_word_result(info), decoded)
            decode.assert_called_once_with('encoded', '2_test')
    
    def test_invalid_word_response_is_reported(self):
        for result in ({'data': {'word_list': None}}, {'word_list': None}):
            with self.subTest(result = result):
                info = SimpleNamespace(get_word_list_result = result)
                with self.assertRaisesRegex(ValueError, '有效词表'):
                    word_list.decode_word_result(info)
    
    def test_invalid_entry_does_not_poison_current_or_persisted_vocabulary(self):
        for invalid in ({'word': 42, 'word_zh': '无效'}, None):
            with self.subTest(entry = invalid):
                info = SimpleNamespace(
                        word_list = ['existing'], word_dict = {'原有': 'existing'}, settings = Settings( ),
                        get_word_list_result = {'word_list': [{'word': 'valid', 'word_zh': '有效'}, invalid]},
                )
                with patch('easy_cidaren.core.word_list.write_json') as write:
                    with self.assertRaisesRegex(ValueError, '词条'):
                        word_list.handle_word_result(info)
                    write.assert_not_called( )
                self.assertEqual(info.word_list, ['existing'])
                self.assertEqual(info.word_dict, {'原有': 'existing'})
    
    def test_missing_meaning_does_not_block_using_words(self):
        info = SimpleNamespace(
                word_dict = {}, settings = Settings( ),
                get_word_list_result = {'word_list': [
                    {'word': 'one'}, {'word': 'two', 'word_zh': None},
                    {'word': 'three', 'word_zh': ''}, {'word': 'four', 'word_zh': '四'},
                ]},
        )
        with patch('easy_cidaren.core.word_list.write_json') as write:
            word_list.handle_word_result(info)
        self.assertEqual(info.word_list, ['one', 'two', 'three', 'four'])
        self.assertEqual(info.word_dict, {'四': 'four'})
        self.assertEqual(write.call_args.args[1], {'四': 'four'})
