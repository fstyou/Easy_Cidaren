import logging
import types
import unittest
from unittest.mock import Mock, patch

from easy_cidaren.core import answer_library
from easy_cidaren.core.settings import Settings
from easy_cidaren.ui import task_worker


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.operations = {}
        for name in ('get_all_unit', 'get_unit_words', 'get_book_all_words', 'get_exam',
                     'select_all_word', 'skip_exam', 'extract_book_word', 'handle_word_result', 'query_word_unit'):
            self.operations[name] = self.enterContext(patch.object(task_worker, name))
        self.state = types.SimpleNamespace(course_id = 'course', get_word_list_result = {}, word_list = [],
                                           now_unit = '', task_id = '', all_unit = {'task_list': []})
    
    def worker(self, tasks = (), *, batch = False):
        worker = task_worker.TaskWorker(self.state, list(tasks), batch_mode = batch)
        worker.logger = logging.getLogger('test_worker')
        self.messages = types.SimpleNamespace( )
        for name in ('task_finished', 'task_error', 'task_progress', 'task_notice', 'batch_finished'):
            messages = []
            setattr(self.messages, name, messages)
            getattr(worker, name).connect(messages.append)
        return worker
    
    def test_single_and_batch_tasks_use_injected_state(self):
        for batch in (False, True):
            with self.subTest(batch = batch):
                tasks = [{'task_name': '任务一'}, {'task_name': '任务二'}] if batch else [{'task_name': '测试任务'}]
                worker = self.worker(tasks, batch = batch)
                worker.complete_test = Mock( )
                worker.run( )
                self.assertIs(worker.public_info, self.state)
                self.assertEqual(worker.complete_test.call_count, len(tasks))
                self.assertEqual(len(self.messages.task_finished), len(tasks))
                if batch:
                    self.assertIn('成功 2 个', self.messages.batch_finished[0])
                else:
                    self.assertEqual(self.messages.batch_finished, [])
    
    def test_stop_interrupts_wait(self):
        worker = self.worker( )
        worker.stop( )
        self.assertTrue(worker._stop_event.wait(0))
    
    def test_fatal_errors_stop_the_whole_batch_without_retry(self):
        worker = self.worker([{'task_name': '任务一'}, {'task_name': '任务二'}], batch = True)
        worker.complete_test = Mock(side_effect = task_worker.UnsafeRequestError('invalid data'))
        worker.run( )
        worker.complete_test.assert_called_once( )
        self.assertIn('invalid data', self.messages.task_error[0])
        self.assertEqual(self.messages.batch_finished, [])
    
    def test_invalid_library_allows_answer_fallback_without_skipping(self):
        self.state.settings = Settings( )
        self.state.exam = {'topic_code': 'first', 'topic_mode': 32}
        worker = self.worker( )
        
        def answer(_info, _mode):
            return answer_library.lookup('含义') or 2
        
        def submit(info, _option, **_kwargs):
            info.exam = 'complete'
        
        with patch.object(answer_library, 'load_lib',
                          side_effect = answer_library.AnswerLibraryError('invalid library')), \
                patch.object(task_worker, 'answer', side_effect = answer), \
                patch.object(task_worker, 'submit', side_effect = submit) as submitted:
            worker.answer_questions( )
        self.assertEqual(submitted.call_args.args[1], 2)
        self.operations['skip_exam'].assert_not_called( )
    
    def test_error_after_stop_is_not_reported_as_task_failure(self):
        worker = self.worker([{'task_name': '停止中的任务'}])
        
        def fail_after_stop(_task):
            worker.stop( )
            raise task_worker.UnsafeRequestError('request ended after stop')
        
        worker.complete_test = fail_after_stop
        worker.run( )
        self.assertEqual(self.messages.task_error, [])
    
    def test_progress_preserves_task_names_with_separators(self):
        self.state.exam = {'topic_done_num': 3, 'topic_total': 10}
        self.state.right_count, self.state.wrong_count, self.state.skip_count = 2, 0, 1
        worker = self.worker( )
        worker.current_index, worker.current_total, worker.current_task_name = 1, 2, '任务 | 1/2'
        worker.emit_progress( )
        progress = self.messages.task_progress[0]
        self.assertEqual((progress.done, progress.total, progress.right, progress.skipped), (3, 10, 2, 1))
        self.assertEqual(progress.task_name, '任务 | 1/2')
    
    def test_selection_failure_prevents_answering(self):
        worker = self.worker( )
        worker.start_answering = Mock( )
        self.operations['select_all_word'].side_effect = RuntimeError('selection failed')
        with self.assertRaisesRegex(RuntimeError, 'selection failed'):
            worker.complete_practice('unit', 0, 1)
        worker.start_answering.assert_not_called( )
    
    def test_new_task_does_not_reuse_previous_vocabulary_or_id(self):
        self.state.word_list, self.state.now_unit, self.state.task_id = ['stale'], 'stale', 'previous'
        worker = self.worker( )
        worker.class_task_answer = Mock( )
        worker.complete_test({'task_name': 'custom', 'course_id': 'course',
                              'release_id': 1, 'task_id': 'current', 'task_type': 2, 'progress': 0})
        self.assertEqual(self.state.word_list, [])
        self.assertEqual(self.state.now_unit, '')
        self.assertEqual(self.state.task_id, 'current')
    
    def test_stop_during_word_request_prevents_selection(self):
        worker = self.worker( )
        self.operations['get_unit_words'].side_effect = lambda _info: worker.stop( )
        worker.complete_practice('unit', 0, 1)
        self.operations['select_all_word'].assert_not_called( )
    
    def test_duplicate_names_require_a_unique_task_id(self):
        self.state.all_unit = {'task_list': [
            {'task_name': '重复名称', 'list_id': 'unit-a', 'task_id': 1},
            {'task_name': '重复名称', 'list_id': 'unit-b', 'task_id': 2},
        ]}
        worker = self.worker( )
        worker.class_task_answer = Mock( )
        task = {'task_name': '重复名称', 'course_id': 'course', 'release_id': 1,
                'task_id': 2, 'task_type': 2, 'progress': 0}
        worker.complete_test(task)
        self.assertEqual(self.state.now_unit, 'unit-b')
        task['task_id'] = 3
        with self.assertRaisesRegex(task_worker.QuestionSkipError, '多个同名课程单元'):
            worker.complete_test(task)
