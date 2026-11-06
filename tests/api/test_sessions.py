import unittest
from unittest.mock import patch

from easy_cidaren.api import sessions


class SessionTests(unittest.TestCase):
    def setUp(self):
        for name in ('query_session', 'answer_session', 'selection_session', 'resource_session'):
            self.enterContext(patch.object(sessions, name, sessions._UninitializedSession( )))
        self.addCleanup(self.close_sessions)
    
    @staticmethod
    def close_sessions( ):
        for session in (sessions.query_session, sessions.answer_session,
                        sessions.selection_session, sessions.resource_session):
            session.close( )
    
    def test_uninitialized_session_rejects_requests(self):
        with self.assertRaisesRegex(RuntimeError, '尚未初始化'):
            sessions.query_session.get('https://example.invalid', timeout = 1)
    
    def test_session_headers_are_independent_and_have_explicit_encoding(self):
        sessions.set_token('first', accept_encoding = 'gzip')
        sessions.query_session.headers['extra'] = 'value'
        for session in (sessions.answer_session, sessions.selection_session, sessions.resource_session):
            self.assertNotIn('extra', session.headers)
            self.assertEqual(session.headers['Accept-Encoding'], 'gzip')
        self.assertNotIn('Usertoken', sessions.base_headers)
        self.assertNotIn('Content-Length', sessions.answer_session.headers)
        self.assertNotIn('Abc', sessions.resource_session.headers)
        self.assertNotIn('Authorization-V', sessions.resource_session.headers)
        self.assertNotEqual(sessions.answer_session.headers['Authorization-V'],
                            sessions.query_session.headers['Authorization-V'])
    
    def test_relogin_closes_previous_connections(self):
        sessions.set_token('first', accept_encoding = 'gzip')
        previous = sessions.query_session
        with patch.object(previous, 'close', wraps = previous.close) as close:
            sessions.set_token('second', accept_encoding = 'gzip, deflate')
        close.assert_called_once( )
        self.assertIsNot(sessions.query_session, previous)
        self.assertEqual(sessions.query_session.headers['Usertoken'], 'second')
