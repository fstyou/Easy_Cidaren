import unittest
from datetime import datetime
from unittest.mock import patch

from easy_cidaren.core.task_selection import batch_tasks, load_class_tasks, task_times, unavailable_reason


class TaskSelectionTests(unittest.TestCase):
    def test_partial_refresh_is_not_returned_after_failure(self):
        first_page = {'records': [{'over_status': 2, 'task_type': 1}], 'total': 20}
        with patch('easy_cidaren.core.task_selection.get_class_task', side_effect = [first_page, OSError('offline')]):
            with self.assertRaises(OSError):
                load_class_tasks(1)

    def test_pages_are_filtered_by_task_type_and_expiry(self):
        learning = {'task_type': 1, 'over_status': 2}
        testing = {'task_type': 2, 'over_status': 2}
        expired = {'task_type': 1, 'over_status': 3}
        pages = [{'records': [learning, testing, expired], 'total': 11},
                 {'records': [learning], 'total': 11}]
        with patch('easy_cidaren.core.task_selection.get_class_task', side_effect = pages) as request:
            self.assertEqual(load_class_tasks(1), [learning, learning])
        self.assertEqual([call.args for call in request.call_args_list], [(1,), (2,)])

    def test_empty_page_with_more_results_is_rejected(self):
        with patch('easy_cidaren.core.task_selection.get_class_task', return_value = {'records': [], 'total': 30}):
            with self.assertRaisesRegex(ValueError, '分页数据不完整'):
                load_class_tasks(1)

    def test_cancellation_discards_partial_results_and_stops_paging(self):
        cancelled = [False]

        def first_page(_page):
            cancelled[0] = True
            return {'records': [{'over_status': 2, 'task_type': 1}], 'total': 20}

        with patch('easy_cidaren.core.task_selection.get_class_task', side_effect = first_page) as request:
            self.assertEqual(load_class_tasks(1, cancelled = lambda: cancelled[0]), [])
            request.assert_called_once_with(1)
            request.reset_mock( )
            self.assertEqual(load_class_tasks(1, cancelled = lambda: True), [])
            request.assert_not_called( )
    
    def test_task_times_use_start_plus_duration_in_local_time(self):
        start = 1793604627860
        duration = 115172140
        self.assertEqual(task_times({'start_time': start, 'over_time': duration}),
                         (datetime.fromtimestamp(start / 1000).strftime('%Y-%m-%d %H:%M'),
                          datetime.fromtimestamp((start + duration) / 1000).strftime('%Y-%m-%d %H:%M')))
        self.assertEqual(task_times({}), ('—', '—'))
        self.assertEqual(task_times({'start_time': -1, 'over_time': 2}), ('—', '—'))
        self.assertEqual(task_times({'start_time': 10 ** 30, 'over_time': 1}), ('—', '—'))
    
    def test_not_yet_open_task_is_unavailable_for_both_types(self):
        self.assertIn('尚未开始', unavailable_reason({'over_status': 1, 'progress': 0}))
    
    def test_open_task_with_zero_progress_is_available(self):
        self.assertIsNone(unavailable_reason({'over_status': 2, 'progress': 0}))
    
    def test_completed_tasks_cannot_be_retried(self):
        for task_type in (1, 2):
            task = {'over_status': 2, 'progress': 100, 'task_type': task_type}
            self.assertIn('已完成', unavailable_reason(task))
    
    def test_batch_skips_unopened_and_completed_tasks(self):
        tasks = [
            {'over_status': 1, 'progress': 0},
            {'over_status': 2, 'progress': 0},
            {'over_status': 2, 'progress': 100},
            {'over_status': 3, 'progress': 0},
        ]
        self.assertEqual(batch_tasks(tasks), [tasks[1]])


if __name__ == '__main__':
    unittest.main( )
