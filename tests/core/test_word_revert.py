import types
import unittest
from unittest.mock import Mock, patch

from easy_cidaren.utils import word_revert


class WordRevertTests(unittest.TestCase):
    def setUp(self):
        word_revert._load_model.cache_clear( )
        self.addCleanup(word_revert._load_model.cache_clear)
        self.model = Mock(side_effect = lambda word: [types.SimpleNamespace(lemma_ = word.lower( ))])
        self.load = self.enterContext(patch.object(word_revert.spacy, 'load', return_value = self.model))
        self.fallback = self.enterContext(patch.object(word_revert, 'use_api_get_prototype', return_value = 'fallback'))
    
    def test_model_is_reused(self):
        self.assertEqual(word_revert.word_revert('ONE'), 'one')
        self.assertEqual(word_revert.word_revert('two'), 'two')
        self.load.assert_called_once( )
        self.fallback.assert_not_called( )
    
    def test_model_failure_falls_back_to_api(self):
        self.load.side_effect = RuntimeError('model unavailable')
        self.assertEqual(word_revert.word_revert('word'), 'fallback')
        self.fallback.assert_called_once_with('word')
        self.fallback.return_value = None
        with self.assertRaisesRegex(ValueError, '无法获取单词原型'):
            word_revert.word_revert('missing')
    
    def test_empty_model_result_uses_api_fallback(self):
        self.model.side_effect = None
        for result in ([], [types.SimpleNamespace(lemma_ = '')]):
            with self.subTest(result = result):
                self.model.return_value = result
                self.assertEqual(word_revert.word_revert('empty'), 'fallback')
        self.assertEqual(self.fallback.call_count, 2)


if __name__ == '__main__':
    unittest.main( )
