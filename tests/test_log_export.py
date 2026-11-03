import logging
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from easy_cidaren.app_logging.export import export_log


class LogExportTests(unittest.TestCase):
    def test_exports_current_log_and_logging_continues(self):
        with TemporaryDirectory( ) as directory:
            source = Path(directory) / 'app.log'
            destination = Path(directory) / 'export.log'
            logger = logging.getLogger('test.log_export')
            handler = logging.FileHandler(source, encoding = 'utf-8')
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
            try:
                logger.info('导出前')
                export_log(source, destination)
                logger.info('导出后')
                self.assertIn('导出前', destination.read_text(encoding = 'utf-8'))
                self.assertNotIn('导出后', destination.read_text(encoding = 'utf-8'))
                self.assertIn('导出后', source.read_text(encoding = 'utf-8'))
            finally:
                logger.removeHandler(handler)
                handler.close( )
    
    def test_rejects_export_to_current_log(self):
        with TemporaryDirectory( ) as directory:
            source = Path(directory) / 'app.log'
            source.write_text('日志', encoding = 'utf-8')
            with self.assertRaises(OSError):
                export_log(source, source)
            self.assertEqual(source.read_text(encoding = 'utf-8'), '日志')


if __name__ == '__main__':
    unittest.main( )
