import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from easy_cidaren.core import answer_library as library


class AnswerLibraryTests(unittest.TestCase):
    def setUp(self):
        directory = self.enterContext(tempfile.TemporaryDirectory( ))
        self.root = Path(directory)
        self.enterContext(patch.object(library, 'DATA_DIR', self.root))
        self.enterContext(patch.object(library, '_lib', None))

    def test_phrase_and_word_answers_share_storage_without_mixing(self):
        library.add_answer('含义', ['a phrase'])
        library.add_answer('含义', ['a phrase'])
        library.add_answer('单条', 'whole phrase')
        self.assertEqual(library.lookup('单条'), ['whole phrase'])
        library.add_word_answer('含义', ['word'])
        self.assertEqual(library.lookup('含义'), ['a phrase'])
        self.assertEqual(library.lookup_word('含义'), ['word'])
        saved = json.loads((self.root / 'answer_lib.json').read_text(encoding = 'utf-8'))
        self.assertEqual(saved['含义'], ['a phrase'])
        self.assertEqual(saved['_word_answers']['含义'], ['word'])

    def test_failed_save_does_not_change_cached_answers(self):
        with patch('easy_cidaren.core.answer_library.write_json', side_effect = OSError('failed')):
            library.add_answer('新含义', ['new answer'])
        self.assertIsNone(library.lookup('新含义'))
        library.add_answer('新含义', ['new answer'])
        saved = json.loads((self.root / 'answer_lib.json').read_text(encoding = 'utf-8'))
        self.assertEqual(saved['新含义'], ['new answer'])

    def test_invalid_library_is_not_used_or_overwritten(self):
        path = self.root / 'answer_lib.json'
        for invalid in ([], None, {'含义': 'whole phrase'}, {'含义': [1]},
                        {'_word_answers': []}, {'_word_answers': {'含义': 'word'}}):
            with self.subTest(value = invalid):
                original = json.dumps(invalid)
                path.write_text(original, encoding = 'utf-8')
                self.assertIsNone(library.lookup('含义'))
                self.assertIsNone(library.lookup_word('含义'))
                library.add_answer('含义', ['new answer'])
                library.add_word_answer('含义', ['new word'])
                self.assertIsNone(library._lib)
                self.assertEqual(path.read_text(encoding = 'utf-8'), original)

    def test_unreadable_library_has_actionable_error(self):
        path = self.root / 'answer_lib.json'
        for content in (b'{invalid json', b'\xff'):
            with self.subTest(content = content):
                path.write_bytes(content)
                with self.assertRaisesRegex(library.AnswerLibraryError, 'answer_lib.json'):
                    library.load_lib( )
                self.assertIsNone(library._lib)
        with patch.object(Path, 'open', side_effect = PermissionError('denied')):
            with self.assertRaises(library.AnswerLibraryError):
                library.load_lib( )
            self.assertIsNone(library.lookup('含义'))
            self.assertIsNone(library.lookup_word('含义'))
            with patch.object(library, '_save_lib') as save:
                library.add_answer('含义', ['new answer'])
                save.assert_not_called( )

    def test_valid_existing_answers_are_preserved_when_learning(self):
        path = self.root / 'answer_lib.json'
        path.write_text(json.dumps({'含义': ['old phrase'], '_word_answers': {'含义': ['word']}}),
                        encoding = 'utf-8')
        library.add_answer('含义', ['new phrase'])
        self.assertEqual(library.lookup('含义'), ['old phrase', 'new phrase'])
        self.assertEqual(library.lookup_word('含义'), ['word'])
