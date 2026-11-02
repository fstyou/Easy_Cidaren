import unittest
from types import SimpleNamespace
from unittest.mock import patch

from easy_cidaren.core.answer_result import record_answer_result


class AnswerResultTests(unittest.TestCase):
    def test_result_updates_counts_topic_and_correct_answer_library(self):
        with patch('easy_cidaren.core.answer_result.add_answer') as phrase, \
                patch('easy_cidaren.core.answer_result.add_word_answer') as word:
            for mode, corrects, expected in [(32, ['a phrase'], ['a phrase']),
                                             (73, ['word'], ['word']),
                                             (42, [1, 9], ['second'])]:
                with self.subTest(mode = mode):
                    phrase.reset_mock( )
                    word.reset_mock( )
                    info = SimpleNamespace(
                            right_count = 0, wrong_count = 0, topic_code = 'old', _self_learn_lib = True,
                            exam = {'topic_mode': mode, 'stem': {'remark': '含义'},
                                    'options': [{'content': 'first'}, {'content': 'second'}]},
                    )
                    record_answer_result(info, {'answer_result': 1, 'answer_corrects': corrects,
                                                'topic_code': 'next'})
                    self.assertEqual((info.right_count, info.wrong_count, info.topic_code), (1, 0, 'next'))
                    (phrase if mode == 32 else word).assert_called_once_with('含义', expected)
                    (word if mode == 32 else phrase).assert_not_called( )
    
    def test_disabled_learning_still_records_progress(self):
        info = SimpleNamespace(right_count = 0, wrong_count = 0, topic_code = 'old', _self_learn_lib = False,
                               exam = {'topic_mode': 32, 'stem': {'remark': '含义'}})
        with patch('easy_cidaren.core.answer_result.add_answer') as add:
            record_answer_result(info, {'answer_result': 2, 'answer_corrects': ['answer'],
                                        'topic_code': 'next'})
            add.assert_not_called( )
        self.assertEqual((info.right_count, info.wrong_count, info.topic_code), (0, 1, 'next'))


if __name__ == '__main__':
    unittest.main( )
