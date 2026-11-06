import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from easy_cidaren.core import public_info
from easy_cidaren.core.settings import Settings


class PublicInfoTests(unittest.TestCase):
    def setUp(self):
        directory = self.enterContext(tempfile.TemporaryDirectory( ))
        self.root = Path(directory)
        self.enterContext(patch.object(public_info, 'DATA_DIR', self.root))
        self.enterContext(patch.object(public_info, 'RUNTIME_DIR', self.root / 'runtime'))
    
    def test_settings_saved_only_after_successful_write(self):
        info = public_info.PublicInfo( )
        info.save_settings(min_time = 3, max_time = 5, theme = 'dark', music_path = '提示音.wav')
        saved = Settings.load(self.root / 'runtime' / 'settings.json')
        self.assertEqual(saved, info.settings)
        with patch.object(Settings, 'save', side_effect = OSError('failed')):
            with self.assertRaises(OSError):
                info.save_settings(theme = 'light')
        self.assertEqual(info.settings, saved)
        self.assertEqual(Settings.load(self.root / 'runtime' / 'settings.json'), saved)
    
    def test_defaults_do_not_require_a_configuration_file(self):
        info = public_info.PublicInfo( )
        self.assertEqual(info.settings, Settings( ))
        self.assertFalse((self.root / 'runtime' / 'settings.json').exists( ))
        self.assertEqual(info.task_list, [])
        self.assertEqual(info.version, '1.0.0')
    
    def test_word_pool_is_validated_at_startup(self):
        pool = self.root / 'word_pool.json'
        pool.write_text(json.dumps({'含义': 'word'}), encoding = 'utf-8')
        self.assertEqual(public_info.PublicInfo( ).word_dict, {'含义': 'word'})
        for invalid in ([], {'含义': ['word']}):
            with self.subTest(value = invalid):
                pool.write_text(json.dumps(invalid), encoding = 'utf-8')
                with self.assertRaisesRegex(ValueError, '词表池'):
                    public_info.PublicInfo( )
