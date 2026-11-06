import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from easy_cidaren.api import courses


class CourseTests(unittest.TestCase):
    def test_book_download_checks_http_status_before_reading_json(self):
        response = Mock( )
        response.raise_for_status.side_effect = OSError('HTTP failure')
        state = SimpleNamespace(course_id = 'course', get_book_words_data = [])
        with patch.object(courses.sessions.resource_session, 'get', return_value = response):
            with self.assertRaisesRegex(OSError, 'HTTP failure'):
                courses.get_book_all_words(state)
        response.json.assert_not_called( )
        self.assertEqual(state.get_book_words_data, [])
    
    def test_word_query_passes_word_as_parameter_and_preserves_unicode(self):
        response = Mock( )
        with patch.object(courses.sessions.query_session, 'get', return_value = response) as get, \
                patch('easy_cidaren.api.courses.create_timestamp', return_value = 123):
            for meaning, expected in [('<span>test</span>', 'test'), (r'<span>测试\u4e2d</span>', '测试中')]:
                with self.subTest(meaning = meaning):
                    response.json.return_value = {'code': 1, 'data': {'word_mean': {'meaning': meaning}}}
                    self.assertEqual(courses.use_api_get_prototype('a&b'), expected)
                    self.assertEqual(get.call_args.kwargs['params']['word'], 'a&b')
                    self.assertEqual(get.call_args.kwargs['params']['timestamp'], 123)
