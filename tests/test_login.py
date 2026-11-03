import unittest
from unittest.mock import Mock, patch

from requests import exceptions

from easy_cidaren.api.login import verify_token


class LoginErrorTests(unittest.TestCase):
    def test_network_errors_return_the_expected_status(self):
        cases = [(exceptions.Timeout, 3), (exceptions.SSLError, 5),
                 (exceptions.ProxyError, 6), (exceptions.ConnectionError, 7)]
        for error, expected in cases:
            with self.subTest(error = error), \
                    patch('easy_cidaren.api.login.requests.set_token'), \
                    patch('easy_cidaren.api.login.requests.rqs_session') as session:
                session.get.side_effect = error('test')
                self.assertEqual(verify_token('test'), expected)

    def test_http_error_returns_status(self):
        response = Mock( )
        response.raise_for_status.side_effect = exceptions.HTTPError('test')
        with patch('easy_cidaren.api.login.requests.set_token'), \
                patch('easy_cidaren.api.login.requests.rqs_session') as session:
            session.get.return_value = response
            self.assertEqual(verify_token('test'), 2)
