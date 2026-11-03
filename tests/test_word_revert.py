import logging
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from tests.module_loader import load_module


class WordRevertTests(unittest.TestCase):
    def test_model_is_reused_and_failure_falls_back_to_api(self):
        model = Mock(side_effect = lambda word: [types.SimpleNamespace(lemma_ = word.lower( ))])
        spacy = types.SimpleNamespace(load = Mock(return_value = model))
        fallback = Mock(return_value = 'fallback')
        logger = types.SimpleNamespace(logger = logging.getLogger('test_word_revert'))
        modules = {
            'spacy': spacy,
            'easy_cidaren.api.courses': types.SimpleNamespace(use_api_get_prototype = fallback),
            'easy_cidaren.app_logging.config': types.SimpleNamespace(Log = lambda name: logger),
        }
        path = Path(__file__).resolve( ).parents[1] / 'easy_cidaren' / 'utils' / 'word_revert.py'
        with patch.dict(sys.modules, modules):
            module = load_module('test_word_revert_module', path)
            self.assertEqual(module.word_revert('ONE'), 'one')
            self.assertEqual(module.word_revert('TWO'), 'two')
            self.assertEqual(spacy.load.call_count, 1)
            module._load_model.cache_clear( )
            spacy.load.side_effect = RuntimeError('model unavailable')
            self.assertEqual(module.word_revert('word'), 'fallback')
            fallback.assert_called_once_with('word')
            fallback.return_value = None
            with self.assertRaisesRegex(ValueError, '无法获取单词原型'):
                module.word_revert('missing')
            spacy.load.side_effect = None
            model.side_effect = None
            model.return_value = []
            module._load_model.cache_clear( )
            with self.assertRaisesRegex(ValueError, '语言模型未返回单词原型'):
                module.word_revert('empty')


if __name__ == '__main__':
    unittest.main( )
