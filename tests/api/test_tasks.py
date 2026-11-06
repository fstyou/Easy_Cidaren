import base64
import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from requests.exceptions import HTTPError, Timeout

from easy_cidaren.api import tasks
from easy_cidaren.api.response import UnknownObfuscationError, UnsafeRequestError
from easy_cidaren.core.question_runner import run_questions


def response(**payload):
    return Mock(json = lambda: payload, text = 'response')


class TaskApiTests(unittest.TestCase):
    def test_plain_question_is_accepted_when_encoding_metadata_is_empty_or_unknown(self):
        question = {'topic_code': 'current', 'topic_mode': 32}
        data = base64.b64encode(json.dumps(question).encode( )).decode( )
        for version in (None, '', 0, '2_unknown'):
            with self.subTest(version = version):
                info = SimpleNamespace(task_id = 'task', release_id = 'release', exam = {})
                with patch.object(tasks.sessions.query_session, 'get',
                                  return_value = response(code = 1, data = data, jv = version)) as get:
                    tasks.get_exam(info)
                get.assert_called_once( )
                self.assertEqual(info.exam, question)
    
    def test_missing_encoding_metadata_allows_plain_responses(self):
        decoded = {'topic_code': 'current', 'topic_mode': 32}
        encoded = base64.b64encode(json.dumps(decoded).encode( )).decode( )
        result = response(code = 1, data = encoded, msg = '')
        info = SimpleNamespace(task_id = 'task', release_id = 'release', exam = {}, topic_code = 'current',
                               is_self_built = False, course_id = 'course', now_unit = 'unit', word_list = [])
        with patch.object(tasks.sessions.query_session, 'get', return_value = result), \
                patch.object(tasks.time, 'sleep'):
            tasks.get_exam(info)
            tasks.query_word(info, 'word')
        self.assertEqual(info.exam, decoded)
        self.assertEqual(info.word_query_result, decoded)
        with patch.object(tasks.sessions.answer_session, 'post', return_value = result):
            self.assertEqual(tasks.submit_result(info, 1), decoded)
    
    def test_read_only_request_retries_unknown_encoding_with_a_bound(self):
        unknown, known = response(jv = 'unknown'), response(jv = '0')
        request = Mock(side_effect = [unknown, known])
        with patch.object(tasks.time, 'sleep'):
            self.assertIs(tasks.request_with_known_jv(request, '/query', retry_unknown = True, params = {'x': 1}),
                          known)
        self.assertEqual(request.call_count, 2)
        self.assertEqual(request.call_args.kwargs, {'params': {'x': 1}, 'timeout': 30})
        request = Mock(return_value = unknown)
        with patch.object(tasks.time, 'sleep'), self.assertRaises(UnknownObfuscationError):
            tasks.request_with_known_jv(request, '/query', retry_unknown = True)
        self.assertEqual(request.call_count, 5)
    
    def test_uncertain_mutation_is_never_retried(self):
        invalid_json = response( )
        invalid_json.json = Mock(side_effect = ValueError('invalid JSON'))
        http_error = response(code = 1)
        http_error.raise_for_status.side_effect = HTTPError('server failure')
        for result in (response(jv = 'unknown'), invalid_json, http_error, Timeout('timeout')):
            with self.subTest(result = result):
                request = Mock(side_effect = result) if isinstance(result, Exception) else Mock(return_value = result)
                with self.assertRaises(UnsafeRequestError):
                    tasks.request_with_known_jv(request, '/mutation')
                request.assert_called_once( )
    
    def test_word_selection_response_ends_start_next_and_skip(self):
        info = SimpleNamespace(exam = {'topic_code': 'previous'}, task_id = 1, release_id = 2,
                               topic_code = 'previous', settings = SimpleNamespace(spend_min_time = 1,
                                                                                   spend_max_time = 1))
        result = response(code = 20001, msg = '需要选词！', data = {'chose_word_list': [{}]}, jv = 'unknown')
        for action, session, method in ((tasks.get_exam, tasks.sessions.query_session, 'get'),
                                        (tasks.next_exam, tasks.sessions.answer_session, 'post'),
                                        (tasks.skip_exam, tasks.sessions.answer_session, 'post')):
            with self.subTest(action = action.__name__), patch.object(session, method,
                                                                      return_value = result) as request:
                info.exam = {'topic_code': 'previous'}
                action(info)
                self.assertEqual(info.exam, 'complete')
                request.assert_called_once( )
        tasks._update_exam(info, response(code = 20004, msg = '任务已完成！'))
        self.assertEqual(info.exam, 'complete')
    
    def test_word_selection_during_task_ends_without_error_or_skip(self):
        info = SimpleNamespace(exam = {'topic_code': 'current', 'topic_mode': 15}, skip_count = 0)
        result = response(code = 20001, msg = '需要选词！', data = {'chose_word_list': [{}]})
        skip, notice, progress = Mock( ), Mock( ), Mock( )
        run_questions(info, running = lambda: True, answer = lambda *_: 1,
                      submit = lambda state, _: tasks._update_exam(state, result), read = Mock( ),
                      skip = skip, progress = progress, notice = notice, logger = Mock( ),
                      fatal_errors = (UnsafeRequestError,), delay = Mock( ))
        self.assertEqual(info.exam, 'complete')
        skip.assert_not_called( )
        notice.assert_not_called( )
        progress.assert_called_once( )
    
    def test_invalid_changed_response_stops_task(self):
        info = SimpleNamespace(exam = {'topic_code': 'previous'})
        for invalid in (response( ), response(code = 1, msg = 'ok')):
            with self.subTest(response = invalid), self.assertRaises(UnsafeRequestError):
                tasks._update_exam(info, invalid)
        self.assertEqual(info.exam, {'topic_code': 'previous'})
    
    def test_invalid_decoded_question_preserves_previous_state(self):
        info = SimpleNamespace(exam = {'topic_code': 'previous'})
        for decoded in (None, [], {}, {'topic_code': ''}):
            with self.subTest(decoded = decoded), patch('easy_cidaren.api.tasks.debase64', return_value = decoded):
                with self.assertRaises(UnsafeRequestError):
                    tasks._update_exam(info, response(code = 1, data = 'encoded', jv = '0'))
                self.assertEqual(info.exam, {'topic_code': 'previous'})
    
    def test_non_object_submission_result_is_an_unsafe_response(self):
        info = SimpleNamespace(topic_code = 'current')
        for decoded in (None, [], 'invalid'):
            with self.subTest(decoded = decoded), \
                    patch.object(tasks.sessions.answer_session, 'post',
                                 return_value = response(code = 1, data = 'encoded', jv = '0')) as post, \
                    patch('easy_cidaren.api.tasks.debase64', return_value = decoded):
                with self.assertRaises(UnsafeRequestError):
                    tasks.submit_result(info, 'answer')
                post.assert_called_once( )
                self.assertEqual(info.topic_code, 'current')
    
    def test_word_selection_does_not_require_a_decodable_response(self):
        result = response(code = 1, msg = '成功', data = {}, jv = 'unknown')
        with patch.object(tasks.sessions.selection_session, 'post', return_value = result) as post:
            tasks.select_all_word({'course:unit': ['word']}, 1)
        self.assertEqual(post.call_count, 1)
    
    def test_class_task_starts_without_ui_initializing_global_state(self):
        info = SimpleNamespace(task_id = 'task', release_id = 'release', exam = {})
        with patch.object(tasks.sessions.query_session, 'get',
                          return_value = response(code = 20004, msg = '任务已完成！')) as get:
            tasks.get_exam(info)
        self.assertTrue(get.call_args.args[0].endswith('/ClassTask/StartAnswer'))
        self.assertEqual(get.call_args.kwargs['params']['release_id'], 'release')
        self.assertEqual(get.call_args.kwargs['params']['task_type'], 2)
        self.assertEqual(info.exam, 'complete')
    
    def test_submission_returns_result_without_mutating_question_state(self):
        result = {'answer_result': 1, 'topic_code': 'next'}
        info = SimpleNamespace(topic_code = 'current', right_count = 0)
        with patch.object(tasks.sessions.answer_session, 'post',
                          return_value = response(code = 1, data = 'encoded', jv = '0')), \
                patch('easy_cidaren.api.tasks.debase64', return_value = result):
            self.assertIs(tasks.submit_result(info, 'answer'), result)
        self.assertEqual((info.topic_code, info.right_count), ('current', 0))
