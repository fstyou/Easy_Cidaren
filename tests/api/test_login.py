import unittest
from unittest.mock import Mock, patch

from requests import exceptions

from easy_cidaren.api.login import verify_token


class LoginErrorTests(unittest.TestCase):
    def test_incomplete_login_response_is_reported_as_a_format_error(self):
        with patch('easy_cidaren.api.login.sessions.set_token'), \
                patch('easy_cidaren.api.login.sessions.query_session') as session:
            for data in ({}, [], None):
                with self.subTest(data = data):
                    session.get.return_value.json.return_value = data
                    self.assertEqual(verify_token('test', accept_encoding = 'gzip'), 4)

    def test_login_rejection_preserves_token_refresh_flow(self):
        response = Mock( )
        response.json.return_value = {'code': 11003}
        with patch('easy_cidaren.api.login.sessions.set_token'), \
                patch('easy_cidaren.api.login.sessions.query_session') as session:
            session.get.return_value = response
            self.assertEqual(verify_token('test', accept_encoding = 'gzip'), 1)

    def test_network_errors_return_the_expected_status(self):
        cases = [(exceptions.Timeout, 3), (exceptions.SSLError, 5),
                 (exceptions.ProxyError, 6), (exceptions.ConnectionError, 7)]
        for error, expected in cases:
            with self.subTest(error = error), \
                    patch('easy_cidaren.api.login.sessions.set_token'), \
                    patch('easy_cidaren.api.login.sessions.query_session') as session:
                session.get.side_effect = error('test')
                self.assertEqual(verify_token('test', accept_encoding = 'gzip'), expected)
    
    def test_http_error_returns_status(self):
        response = Mock( )
        response.raise_for_status.side_effect = exceptions.HTTPError('test')
        with patch('easy_cidaren.api.login.sessions.set_token'), \
                patch('easy_cidaren.api.login.sessions.query_session') as session:
            session.get.return_value = response
            self.assertEqual(verify_token('test', accept_encoding = 'gzip'), 2)
