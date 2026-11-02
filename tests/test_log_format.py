import io
import logging
import unittest

from easy_cidaren.logging.format import ConsoleFilter, ConsoleFormatter, MAX_CONSOLE_MESSAGE, console_level


class ConsoleLoggingTests(unittest.TestCase):
    def test_level_selection_preserves_debug_default(self):
        self.assertEqual(console_level(None), logging.DEBUG)
        self.assertEqual(console_level(' info '), logging.INFO)
        self.assertEqual(console_level('unexpected'), logging.DEBUG)
    
    def test_long_diagnostic_is_shortened_without_mutating_file_record(self):
        message = 'x' * (MAX_CONSOLE_MESSAGE + 20)
        record = logging.LogRecord('worker', logging.DEBUG, __file__, 1, '%s', (message,), None)
        rendered = ConsoleFormatter( ).format(record)
        self.assertIn('DEBUG', rendered)
        self.assertIn('worker', rendered)
        self.assertIn('详见日志文件', rendered)
        self.assertNotIn(message, rendered)
        self.assertEqual(record.getMessage( ), message)
    
    def test_file_only_data_and_level_filter_do_not_reach_console(self):
        stream = io.StringIO( )
        handler = logging.StreamHandler(stream)
        handler.setLevel(console_level('INFO'))
        handler.addFilter(ConsoleFilter( ))
        handler.setFormatter(ConsoleFormatter( ))
        logger = logging.getLogger('test.console_levels')
        logger.handlers = [handler]
        logger.setLevel(logging.DEBUG)
        logger.propagate = False
        try:
            logger.debug('debug detail')
            logger.info('task started')
            logger.info('raw response', extra = {'file_only': True})
            logger.warning('task skipped')
            output = stream.getvalue( )
            self.assertIn('INFO', output)
            self.assertIn('task started', output)
            self.assertIn('WARNING', output)
            self.assertNotIn('debug detail', output)
            self.assertNotIn('raw response', output)
        finally:
            logger.removeHandler(handler)
            handler.close( )
    
    def test_error_message_is_not_truncated(self):
        message = 'x' * (MAX_CONSOLE_MESSAGE + 20)
        record = logging.LogRecord('worker', logging.ERROR, __file__, 1, message, (), None)
        self.assertIn(message, ConsoleFormatter( ).format(record))


if __name__ == '__main__':
    unittest.main( )
