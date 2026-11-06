import logging
import unittest
from types import SimpleNamespace

from easy_cidaren.core.question_runner import QuestionSkipError, run_questions


class SecurityError(Exception):
    pass


def question(code, mode = 15):
    return {'topic_code': code, 'topic_mode': mode, 'topic_done_num': 0, 'topic_total': 2}


class QuestionRunnerTests(unittest.TestCase):
    def setUp(self):
        self.info = SimpleNamespace(exam = question('first'), topic_code = None, skip_count = 0)
        self.notices = []
        self.progress = []
        self.skips = []
        self.delays = []
        self.logger = logging.getLogger('test-question-runner')
        self.logger.disabled = True
    
    def run_loop(self, answer, submit, skip = None, read = None):
        run_questions(
                self.info, running = lambda: True, answer = answer, submit = submit,
                read = read or (lambda info: None), skip = skip or self.skip,
                progress = lambda: self.progress.append(True), notice = self.notices.append,
                logger = self.logger, fatal_errors = (SecurityError,), delay = lambda: self.delays.append(True),
        )
    
    def skip(self, info):
        self.skips.append(info.topic_code)
        info.exam = question('second')
    
    def test_answer_error_skips_only_failed_question_and_continues(self):
        def answer(info, _mode):
            if info.exam['topic_code'] == 'first':
                raise ValueError('bad question')
            return 1
        
        self.run_loop(answer, lambda info, option: setattr(info, 'exam', 'complete'))
        self.assertEqual(self.skips, ['first'])
        self.assertEqual(self.info.skip_count, 1)
        self.assertEqual(len(self.progress), 2)
        self.assertEqual(len(self.notices), 1)
        self.assertIn('已跳过', self.notices[0])
    
    def test_no_answer_skips(self):
        self.run_loop(lambda info, mode: None, lambda *_: None,
                      skip = lambda info: setattr(info, 'exam', 'complete'))
        self.assertEqual(self.info.skip_count, 1)
    
    def test_stop_during_answer_calculation_does_not_submit_or_skip(self):
        running = [True]
        submitted = []

        def answer(*_):
            running[0] = False
            return 1

        run_questions(self.info, running = lambda: running[0], answer = answer,
                      submit = lambda *args: submitted.append(args), read = lambda *_: None,
                      skip = self.skip, progress = lambda: None, notice = self.notices.append,
                      logger = self.logger, fatal_errors = (SecurityError,), delay = lambda: None)
        self.assertEqual(submitted, [])
        self.assertEqual(self.skips, [])

    def test_failed_skip_is_reported_and_does_not_loop(self):
        def failed_skip(_info):
            raise OSError('offline')
        
        with self.assertRaises(QuestionSkipError):
            self.run_loop(lambda *_: None, lambda *_: None, skip = failed_skip)
        self.assertEqual(self.info.skip_count, 0)
        self.assertEqual(self.notices, [])
    
    def test_same_question_after_skip_stops(self):
        with self.assertRaises(QuestionSkipError):
            self.run_loop(lambda *_: None, lambda *_: None, skip = lambda info: None)
        self.assertEqual(self.info.skip_count, 0)
    
    def test_security_error_is_not_skipped(self):
        def answer(*_):
            raise SecurityError('verify')
        
        with self.assertRaises(SecurityError):
            self.run_loop(answer, lambda *_: None)
        self.assertEqual(self.skips, [])
    
    def test_unsafe_response_error_stops_without_skipping(self):
        from easy_cidaren.api.response import UnknownObfuscationError
        def answer(*_):
            raise UnknownObfuscationError('unknown version')

        with self.assertRaises(UnknownObfuscationError):
            run_questions(self.info, running = lambda: True, answer = answer, submit = lambda *_: None,
                          read = lambda *_: None, skip = self.skip, progress = lambda: None,
                          notice = self.notices.append, logger = self.logger,
                          fatal_errors = (SecurityError, UnknownObfuscationError), delay = lambda: None)
        self.assertEqual(self.skips, [])

    def test_error_after_server_advanced_does_not_skip_next_question(self):
        def submit(info, _option):
            if info.exam['topic_code'] == 'first':
                info.exam = question('second')
                raise ValueError('local post-processing failed')
            info.exam = 'complete'
        
        self.run_loop(lambda *_: 1, submit)
        self.assertEqual(self.skips, [])
        self.assertEqual(self.info.skip_count, 0)
        self.assertEqual(len(self.delays), 1)

    def test_stop_after_server_advanced_does_not_emit_late_notices(self):
        running = [True]

        def submit(info, _option):
            running[0] = False
            info.exam = question('second')
            raise ValueError('local post-processing failed')

        run_questions(self.info, running = lambda: running[0], answer = lambda *_: 1,
                      submit = submit, read = lambda *_: None, skip = self.skip,
                      progress = lambda: self.progress.append(True), notice = self.notices.append,
                      logger = self.logger, fatal_errors = (SecurityError,), delay = lambda: None)
        self.assertEqual(self.skips, [])
        self.assertEqual(self.progress, [])
        self.assertEqual(self.notices, [])


if __name__ == '__main__':
    unittest.main( )
