from tests.module_loader import load_module

import logging
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


class Signal:
    def __init__(self):
        self.messages = []
    
    def emit(self, value):
        self.messages.append(value)


class WorkerTests(unittest.TestCase):
    def test_worker_uses_injected_state_for_single_and_batch_tasks(self):
        qt = types.ModuleType('PyQt6')
        qt_core = types.ModuleType('PyQt6.QtCore')
        qt_core.QThread = type('QThread', (), {})
        qt_core.pyqtSignal = lambda *args: Signal( )
        qt.QtCore = qt_core
        logger = types.SimpleNamespace(logger = logging.getLogger('test_worker'))
        modules = {
            'PyQt6': qt,
            'PyQt6.QtCore': qt_core,
            'easy_cidaren.api.courses': types.SimpleNamespace(
                    get_all_unit = Mock( ), get_unit_words = Mock( ), get_book_all_words = Mock( )),
            'easy_cidaren.api.tasks': types.SimpleNamespace(
                    get_exam = Mock( ), select_all_word = Mock( ), skip_exam = Mock( )),
            'easy_cidaren.api.response': types.SimpleNamespace(
                    SecurityVerifyError = type('SecurityVerifyError', (Exception,), {})),
            'easy_cidaren.core.answers': types.SimpleNamespace(answer = Mock( ), jump_read = Mock( ), submit = Mock( )),
            'easy_cidaren.app_logging.config': types.SimpleNamespace(Log = lambda name: logger),
            'easy_cidaren.security.decode': types.SimpleNamespace(debase64 = Mock( )),
            'easy_cidaren.core.word_list': types.SimpleNamespace(
                    extract_book_word = Mock( ), handle_word_result = Mock( ), query_word_unit = Mock( )),
        }
        path = Path(__file__).resolve( ).parents[1] / 'easy_cidaren' / 'ui' / 'task_worker.py'
        with patch.dict(sys.modules, modules):
            module = load_module('test_task_worker_module', path)
            state = object( )
            worker = module.TaskWorker(state, [{'task_name': '测试任务'}], batch_mode = False)
            worker.stop( )
            self.assertTrue(worker._stop_event.wait(0))
            worker = module.TaskWorker(state, [{'task_name': '测试任务'}], batch_mode = False)
            worker.complete_test = Mock( )
            worker.run( )
            self.assertIs(worker.public_info, state)
            worker.complete_test.assert_called_once( )
            self.assertIn('测试任务', worker.task_finished.messages[-1])
            
            worker = module.TaskWorker(state, [{'task_name': '任务一'}, {'task_name': '任务二'}], batch_mode = True)
            worker.complete_test = Mock( )
            worker.run( )
            self.assertEqual(worker.complete_test.call_count, 2)
            self.assertIn('成功 2 个', worker.batch_finished.messages[-1])

            # A failed word-selection request must reach task retry handling.
            state = types.SimpleNamespace(course_id = 'course', get_word_list_result = {}, word_list = ['word'])
            worker = module.TaskWorker(state, [], batch_mode = False)
            worker.start_answering = Mock( )
            modules['easy_cidaren.api.tasks'].select_all_word.side_effect = RuntimeError('selection failed')
            with self.assertRaisesRegex(RuntimeError, 'selection failed'):
                worker.complete_practice('unit', 0, 1)
            worker.start_answering.assert_not_called( )

            # Starting another task must not reuse the previous task's vocabulary.
            state.word_list = ['stale']
            state.now_unit = 'stale'
            state.all_unit = {'task_list': []}
            worker.class_task_answer = Mock( )
            worker.complete_test({'task_name': 'custom', 'course_id': 'course',
                                  'release_id': 1, 'task_type': 2, 'progress': 0})
            self.assertEqual(state.word_list, [])
            self.assertEqual(state.now_unit, '')


if __name__ == '__main__':
    unittest.main( )
