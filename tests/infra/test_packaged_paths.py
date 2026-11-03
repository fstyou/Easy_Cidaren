import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from easy_cidaren.paths import initialize_seed_data, user_data_root


class PackagedPathTests(unittest.TestCase):
    def test_platform_data_locations(self):
        home = Path.cwd() / 'example-home'
        xdg = Path.cwd() / 'example-xdg'
        local = Path.cwd() / 'example-local'
        self.assertEqual(user_data_root('darwin', home, {}),
                         home / 'Library' / 'Application Support' / 'EasyCidaren')
        self.assertEqual(user_data_root('linux', home, {'XDG_DATA_HOME': str(xdg)}),
                         xdg / 'EasyCidaren')
        self.assertEqual(user_data_root('linux', home, {'XDG_DATA_HOME': 'relative'}),
                         home / '.local/share/EasyCidaren')
        self.assertEqual(user_data_root('win32', home, {'LOCALAPPDATA': str(local)}),
                         local / 'EasyCidaren')
    
    def test_seed_files_are_copied_once_without_overwriting_user_data(self):
        with tempfile.TemporaryDirectory( ) as directory:
            root = Path(directory)
            source, destination = root / 'resources', root / 'user'
            source.mkdir( )
            (source / 'answer_lib.json').write_text('seed', encoding = 'utf-8')
            initialize_seed_data(source, destination)
            self.assertEqual((destination / 'answer_lib.json').read_text(encoding = 'utf-8'), 'seed')
            (destination / 'answer_lib.json').write_text('user data', encoding = 'utf-8')
            initialize_seed_data(source, destination)
            self.assertEqual((destination / 'answer_lib.json').read_text(encoding = 'utf-8'), 'user data')
    
    def test_seed_is_fully_written_before_it_becomes_visible(self):
        with tempfile.TemporaryDirectory( ) as directory:
            root = Path(directory)
            source, destination = root / 'resources', root / 'user'
            source.mkdir( )
            (source / 'answer_lib.json').write_text('complete', encoding = 'utf-8')
            from easy_cidaren import paths
            real_link = paths.os.link
            
            def verify_link(temporary, target):
                self.assertFalse(Path(target).exists( ))
                self.assertEqual(Path(temporary).read_text(encoding = 'utf-8'), 'complete')
                real_link(temporary, target)
            
            with patch.object(paths.os, 'link', side_effect = verify_link):
                initialize_seed_data(source, destination)
            self.assertEqual(list(destination.iterdir( )), [destination / 'answer_lib.json'])
    
    def test_concurrent_creation_preserves_existing_data(self):
        with tempfile.TemporaryDirectory( ) as directory:
            root = Path(directory)
            source, destination = root / 'resources', root / 'user'
            source.mkdir( )
            (source / 'answer_lib.json').write_text('seed', encoding = 'utf-8')
            from easy_cidaren import paths
            def concurrent_create(_temporary, target):
                Path(target).write_text('user data', encoding = 'utf-8')
                raise FileExistsError
            
            with patch.object(paths.os, 'link', side_effect = concurrent_create):
                initialize_seed_data(source, destination)
            self.assertEqual((destination / 'answer_lib.json').read_text(encoding = 'utf-8'), 'user data')
            self.assertEqual(list(destination.iterdir( )), [destination / 'answer_lib.json'])
