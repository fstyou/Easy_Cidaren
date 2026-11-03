import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from tests import PROJECT_ROOT
from tests.module_loader import load_module


class FakeLog:
    def __init__(self, name):
        pass
    
    def error(self, *args):
        pass


class AnswerLibraryTests(unittest.TestCase):
    def test_phrase_and_word_answers_share_storage_without_mixing(self):
        path = PROJECT_ROOT / 'easy_cidaren' / 'core' / 'answer_library.py'
        with tempfile.TemporaryDirectory( ) as directory:
            modules = {
                'easy_cidaren.app_logging.config': types.SimpleNamespace(Log = FakeLog),
                'easy_cidaren.paths': types.SimpleNamespace(DATA_DIR = Path(directory)),
            }
            with patch.dict(sys.modules, modules):
                library = load_module('test_answer_library_module', path)
                library.add_answer('含义', ['a phrase'])
                library.add_answer('含义', ['a phrase'])
                library.add_word_answer('含义', ['word'])
                self.assertEqual(library.lookup('含义'), ['a phrase'])
                self.assertEqual(library.lookup_word('含义'), ['word'])
                saved = json.loads((Path(directory) / 'answer_lib.json').read_text(encoding = 'utf-8'))
                self.assertEqual(saved['含义'], ['a phrase'])
                self.assertEqual(saved['_word_answers']['含义'], ['word'])
                with patch.object(library, 'write_json', side_effect = OSError('failed')):
                    library.add_answer('新含义', ['new answer'])
                self.assertIsNone(library.lookup('新含义'))
                library.add_answer('新含义', ['new answer'])
                saved = json.loads((Path(directory) / 'answer_lib.json').read_text(encoding = 'utf-8'))
                self.assertEqual(saved['新含义'], ['new answer'])


if __name__ == '__main__':
    unittest.main( )
