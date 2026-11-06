import json
import tempfile
import unittest
from pathlib import Path

from easy_cidaren.core.settings import Settings


class SettingsTests(unittest.TestCase):
    def test_brotli_is_the_single_source_for_accept_encoding(self):
        self.assertEqual(Settings( ).accept_encoding, 'gzip, deflate, br')
        self.assertEqual(Settings(br_choices = False).accept_encoding, 'gzip, deflate')

    def test_invalid_values_fail_before_tasks_start(self):
        for values in ({'min_time': -1}, {'max_time': True}, {'spend_min_time': '2'},
                       {'spend_max_time': 86401}, {'min_time': 3, 'max_time': 1},
                       {'play_music': 'false'}, {'music_path': None}, {'theme': 'unknown'}):
            with self.subTest(values = values), self.assertRaises(ValueError):
                Settings(**values)

    def test_round_trip_keeps_supported_settings_and_omits_derived_fields(self):
        with tempfile.TemporaryDirectory( ) as directory:
            path = Path(directory) / 'settings.json'
            path.write_text(json.dumps({'br_choices': False, 'accept_encoding': 'br',
                                        'self_learn_pool': False, 'theme': 'dark'}), encoding = 'utf-8')
            settings = Settings.load(path)
            self.assertEqual(settings.accept_encoding, 'gzip, deflate')
            self.assertFalse(settings.self_learn_pool)
            settings.save(path)
            self.assertEqual(Settings.load(path), settings)
            self.assertNotIn('accept_encoding', json.loads(path.read_text(encoding = 'utf-8')))

    def test_invalid_file_is_not_silently_overwritten(self):
        with tempfile.TemporaryDirectory( ) as directory:
            path = Path(directory) / 'settings.json'
            for content in ('[]', '{broken', '{"min_time": "bad"}'):
                with self.subTest(content = content):
                    path.write_text(content, encoding = 'utf-8')
                    with self.assertRaises(ValueError):
                        Settings.load(path)
                    self.assertEqual(path.read_text(encoding = 'utf-8'), content)
