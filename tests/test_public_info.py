import importlib.util
import json
import logging
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch


class PublicInfoTests(unittest.TestCase):
    def test_settings_update_the_config(self):
        logger = types.SimpleNamespace(logger = logging.getLogger('test_public_info'))
        path = Path(__file__).resolve( ).parents[1] / 'easy_cidaren' / 'core' / 'public_info.py'
        config = {
            'min_time': 1, 'max_time': 3, 'spend_min_time': 4, 'spend_max_time': 5,
            'br_choices': True, 'accept_encoding': 'gzip',
            'play_music': True, 'music_path': '', 'self_learn_lib': True, 'self_learn_pool': False,
            'custom_field': '保留',
        }
        with tempfile.TemporaryDirectory( ) as directory:
            data_dir = Path(directory) / 'data'
            data_dir.mkdir( )
            runtime_dir = Path(directory) / 'runtime'
            runtime_dir.mkdir( )
            config_path = runtime_dir / 'settings.json'
            config_path.write_text(json.dumps(config), encoding = 'utf-8')
            (data_dir / 'word_pool.json').write_text('{"含义": "word"}', encoding = 'utf-8')
            with patch.dict(sys.modules,
                            {'easy_cidaren.logging.config': types.SimpleNamespace(Log = lambda name: logger)}):
                spec = importlib.util.spec_from_file_location('test_public_info_module', path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                with patch.object(module, 'DATA_DIR', data_dir), patch.object(module, 'RUNTIME_DIR', runtime_dir):
                    info = module.PublicInfo( )
                    self.assertEqual(info.word_dict, {'含义': 'word'})
                    self.assertEqual((info.min_time, info.max_time), (1, 3))
                    with patch.object(module, 'write_json', side_effect = OSError('failed')):
                        with self.assertRaises(OSError):
                            info.input_info(5, 6, 7, 8, False, 'gzip', False, '')
                    self.assertEqual((info.min_time, info.max_time), (1, 3))
                    info.input_info(3, 5, 6, 9, False, 'gzip, deflate', False, '提示音.wav')
                saved = json.loads(config_path.read_text(encoding = 'utf-8'))
                self.assertEqual(saved['min_time'], 3)
                self.assertEqual(saved['music_path'], '提示音.wav')
                self.assertEqual(saved['custom_field'], '保留')
                self.assertFalse(info.play_music)
    
    def test_first_run_creates_settings(self):
        logger = types.SimpleNamespace(logger = logging.getLogger('test_public_info'))
        path = Path(__file__).resolve( ).parents[1] / 'easy_cidaren' / 'core' / 'public_info.py'
        with tempfile.TemporaryDirectory( ) as directory, \
                patch.dict(sys.modules,
                           {'easy_cidaren.logging.config': types.SimpleNamespace(Log = lambda name: logger)}):
            spec = importlib.util.spec_from_file_location('test_public_info_first_run', path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            runtime_dir = Path(directory) / 'runtime'
            with patch.object(module, 'DATA_DIR', Path(directory)), patch.object(module, 'RUNTIME_DIR', runtime_dir):
                info = module.PublicInfo( )
            settings = json.loads((runtime_dir / 'settings.json').read_text(encoding = 'utf-8'))
            self.assertEqual(settings, module.DEFAULT_SETTINGS)
            self.assertEqual(info.version, '1.0.0')


if __name__ == '__main__':
    unittest.main( )
