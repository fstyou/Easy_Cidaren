import unittest
from unittest.mock import Mock

from easy_cidaren.api.response import CardDataError, SecurityVerifyError, handle_response


def response(**data):
    return Mock(json = lambda: data, text = 'response')


class ApiResponseTests(unittest.TestCase):
    def test_success_and_task_completion_codes(self):
        handle_response(response(code = 1))
        handle_response(response(code = 20004), task = True)
        handle_response(response(code = 20001, data = {'done': True}), task = True)
        with self.assertRaises(RuntimeError):
            handle_response(response(code = 20004))
    
    def test_security_and_card_errors_remain_distinct(self):
        for task in (False, True):
            with self.subTest(task = task), self.assertRaises(SecurityVerifyError):
                handle_response(response(code = 11003), task = task)
        with self.assertRaises(CardDataError):
            handle_response(response(code = 120), task = True)
        with self.assertRaises(RuntimeError):
            handle_response(response(code = 120))


if __name__ == '__main__':
    unittest.main( )
