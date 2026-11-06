import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from easy_cidaren.api.response import CardDataError, SecurityVerifyError, UnsafeRequestError
from easy_cidaren.core.answer_selection import select_match_word, select_mean, word_examples
from easy_cidaren.core.answers import answer, complete_sentence, complete_spelling, full_sentence, submit, together_word
from easy_cidaren.core.public_info import PublicInfo


class AnswerSelectionTests(unittest.TestCase):
    def test_sentence_cache_and_examples_encode_options_identically(self):
        for option, word, expected in (
                ({'content': 'word', 'answer_tag': 0}, 'word', 0),
                ({'content': 'word', 'answer_tag': '1#', 'sub_options': []}, 'word', '1#0'),
                ({'content': 'word', 'answer_tag': '1#',
                  'sub_options': [{'content': 'words', 'answer_tag': 2}]}, 'words', '1#2'),
        ):
            for cached in (False, True):
                with self.subTest(option = option, cached = cached):
                    info = SimpleNamespace(word_list = [], exam = {
                        'options': [option], 'stem': {'remark': '含义', 'content': '{}'},
                    })
                    with patch('easy_cidaren.core.answers.lookup_word',
                               return_value = [word.upper( )] if cached else None), \
                            patch('easy_cidaren.core.answers.word_examples', return_value = word) as examples:
                        self.assertEqual(full_sentence(info), expected)
                    if cached:
                        examples.assert_not_called( )
    
    def test_sentence_fallback_uses_complete_option_tag(self):
        for tag, expected in ((2, 2), ('2#', '2#0')):
            with self.subTest(tag = tag):
                info = SimpleNamespace(word_list = [], exam = {
                    'options': [{'content': 'one', 'answer_tag': 0},
                                {'content': 'two', 'answer_tag': 1},
                                {'content': 'three', 'answer_tag': tag}],
                    'stem': {'remark': '含义', 'content': '{}'},
                })
                with patch('easy_cidaren.core.answers.lookup_word', return_value = None), \
                        patch('easy_cidaren.core.answers.word_examples', return_value = ''):
                    self.assertEqual(full_sentence(info), expected)
    
    def test_mean_choice_uses_original_index_when_priority_changes(self):
        info = SimpleNamespace(exam = {'options': [{'content': 'first'}, {'content': 'second'}]},
                               word_list = ['second'], word_means = ['second'])
        self.assertEqual(select_mean(info), 1)
    
    def test_mean_choice_prefers_exact_match_and_preserves_character_order(self):
        info = SimpleNamespace(exam = {'options': [{'content': '人工'}, {'content': '工人或学生'},
                                                   {'content': '工人'}]},
                               word_list = [], word_means = ['工人'])
        self.assertEqual(select_mean(info), 2)
    
    def test_reordered_meaning_clauses_match_without_character_permutation(self):
        info = SimpleNamespace(exam = {'options': [{'content': '无关'}, {'content': '盒子；包装'}]},
                               word_list = [], word_means = ['包装;盒子'])
        with patch('easy_cidaren.core.answer_selection.random.randint',
                   side_effect = AssertionError('unexpected guess')):
            self.assertEqual(select_mean(info), 1)
        info.exam['options'] = [{'content': '人工'}, {'content': '其他'}]
        info.word_means = ['工人']
        with patch('easy_cidaren.core.answer_selection.random.randint', return_value = 1):
            self.assertEqual(select_mean(info), 1)
    
    def test_word_choice_prefers_exact_meaning_over_reordered_match(self):
        info = SimpleNamespace(exam = {'options': [{'content': 'first'}, {'content': 'second'}]},
                               word_list = [], word_means = [])
        
        def query(state, word):
            state.word_means = ['盒子；包装' if word == 'first' else '包装；盒子']
        
        with patch('easy_cidaren.core.answer_selection.query_word', side_effect = query), \
                patch('easy_cidaren.core.answer_selection.handle_query_word_mean'):
            self.assertEqual(select_match_word(info, '包装；盒子'), 1)
            info.exam['options'].pop( )
            self.assertEqual(select_match_word(info, '包装；盒子'), 0)
    
    def test_matching_word_and_relation_use_original_order(self):
        info = SimpleNamespace(exam = {'options': [{'content': 'first'}, {'content': 'second'}],
                                       'stem': {'remark': [{'relation': 'second'}]}},
                               word_list = ['second'], word_means = ['target'])
        with patch('easy_cidaren.core.answer_selection.query_word'), \
                patch('easy_cidaren.core.answer_selection.handle_query_word_mean'):
            self.assertEqual(select_match_word(info, 'target'), 1)
        self.assertEqual(together_word(info), {'second': 1})
    
    def test_unavailable_word_card_does_not_prevent_matching_another_option(self):
        info = SimpleNamespace(exam = {'options': [{'content': 'first'}, {'content': 'second'}]},
                               word_list = ['first', 'second'], word_means = [])
        
        def query(state, word):
            if word == 'first':
                raise CardDataError('卡片不可用')
            state.word_means = ['target']
        
        with patch('easy_cidaren.core.answer_selection.query_word', side_effect = query), \
                patch('easy_cidaren.core.answer_selection.handle_query_word_mean'):
            self.assertEqual(select_match_word(info, 'target'), 1)
        
        with patch('easy_cidaren.core.answer_selection.query_word', side_effect = CardDataError('unavailable')):
            with self.assertRaises(CardDataError):
                select_match_word(info, 'target')
        with patch('easy_cidaren.core.answer_selection.query_word', side_effect = SecurityVerifyError('verify')):
            with self.assertRaises(SecurityVerifyError):
                select_match_word(info, 'target')
    
    def test_examples_continue_after_matching_translation_without_word_markup(self):
        examples = [{'sen_mean_cn': '释义', 'sen_content': 'unmarked sentence'},
                    {'sen_mean_cn': '其他', 'sen_content': '{wrong}'},
                    {'sen_mean_cn': '释义', 'sen_content': 'a {correct} word'}]
        for card in ({'means': [{'usages': [{'examples': examples}]}]},
                     {'options': [{'content': {'example': examples}}]}):
            with self.subTest(card = card):
                info = SimpleNamespace(exam = {'stem': {'remark': '释义'}}, word_query_result = card)
                with patch('easy_cidaren.core.answer_selection.is_word_exist', return_value = True):
                    self.assertEqual(word_examples(info, ['candidate']), 'correct')
    
    def test_unmatched_short_choice_does_not_return_out_of_range_index(self):
        info = SimpleNamespace(exam = {'options': [{'content': 'first'}]},
                               word_list = [], word_means = ['different'])
        with patch('easy_cidaren.core.answer_selection.query_word'), \
                patch('easy_cidaren.core.answer_selection.handle_query_word_mean'):
            self.assertEqual(select_match_word(info, 'target'), 0)
    
    def test_mode_13_fallback_uses_an_existing_option(self):
        for count, expected in ((1, 0), (2, 1), (3, 2), (4, 3), (5, 3)):
            with self.subTest(count = count):
                info = SimpleNamespace(exam = {'options': [{'content': str(i)} for i in range(count)]})
                self.assertEqual(answer(info, 13), expected)
        with self.assertRaisesRegex(ValueError, '没有可选答案'):
            answer(SimpleNamespace(exam = {'options': []}), 13)
    
    def test_spelling_does_not_submit_an_unrelated_last_word(self):
        info = SimpleNamespace(exam = {'w_lens': [4], 'w_tip': 'ca'}, word_list = ['dog', 'bird'])
        with self.assertRaisesRegex(ValueError, '没有匹配前缀'):
            complete_sentence(info)
        info.word_list = ['CAT']
        self.assertEqual(complete_sentence(info), 'CATs')
    
    def test_spelling_accepts_an_unspecified_length(self):
        info = SimpleNamespace(exam = {'stem': {'content': '{ca}', 'remark': '猫'}, 'w_lens': ['']})
        with patch('easy_cidaren.core.answers.lookup', return_value = ['dog cat']):
            self.assertEqual(complete_spelling(info), '["cat"]')
    
    def test_error_processing_a_submitted_answer_stops_the_task(self):
        info = Mock(spec = PublicInfo, exam = {'topic_code': 'current'}, topic_code = '')
        with patch('easy_cidaren.core.answers.submit_result', return_value = {}), \
                patch('easy_cidaren.core.answers.record_answer_result', side_effect = KeyError('topic_code')), \
                patch('easy_cidaren.core.answers.next_exam') as next_exam:
            with self.assertRaises(UnsafeRequestError):
                submit(info, 1)
        next_exam.assert_not_called( )
    
    def test_empty_multiple_answer_does_not_advance_without_submitting(self):
        info = Mock(spec = PublicInfo, exam = {'topic_code': 'current'}, topic_code = '')
        with patch('easy_cidaren.core.answers.submit_result') as submit_result, \
                patch('easy_cidaren.core.answers.next_exam') as next_exam:
            with self.assertRaisesRegex(ValueError, '没有可提交的答案'):
                submit(info, {})
        submit_result.assert_not_called( )
        next_exam.assert_not_called( )
    
    def test_stop_during_multiple_answers_prevents_further_submission(self):
        info = Mock(spec = PublicInfo, exam = {'topic_code': 'current'}, topic_code = '')
        running = [True]
        
        def submit_once(*_):
            running[0] = False
            return {'topic_code': 'next'}
        
        with patch('easy_cidaren.core.answers.submit_result', side_effect = submit_once) as submit_result, \
                patch('easy_cidaren.core.answers.record_answer_result'), \
                patch('easy_cidaren.core.answers.next_exam') as next_exam:
            submit(info, {'first': 1, 'second': 2}, running = lambda: running[0])
        submit_result.assert_called_once( )
        next_exam.assert_not_called( )
