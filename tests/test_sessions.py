import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.module_loader import load_module


class SessionTests(unittest.TestCase):
    def test_uninitialized_session_rejects_requests(self):
        from easy_cidaren.api.sessions import _UninitializedSession

        with self.assertRaisesRegex(RuntimeError, '尚未初始化'):
            _UninitializedSession( ).get('https://example.invalid', timeout = 1)

    def test_login_sessions_have_independent_headers(self):
        requests = types.ModuleType('requests')
        requests.exceptions = types.SimpleNamespace( )
        requests.Session = type('Session', (), {})
        requests.session = lambda: types.SimpleNamespace(headers = {})
        modules = {
            'requests': requests,
            'easy_cidaren.core.public_info': types.SimpleNamespace(
                    PublicInfo = lambda: types.SimpleNamespace(accept_encoding = 'gzip')),
            'easy_cidaren.security.signing': types.SimpleNamespace(encrypt_md5 = lambda value: 'signature'),
        }
        path = Path(__file__).resolve( ).parents[1] / 'easy_cidaren' / 'api' / 'sessions.py'
        with patch.dict(sys.modules, modules):
            module = load_module('test_sessions_module', path)
            module.set_token('first')
            module.rqs_session.headers['extra'] = 'value'
            self.assertNotIn('extra', module.class_task_request.headers)
            self.assertNotIn('Usertoken', module.base_headers)
            self.assertNotIn('Content-Length', module.rqs2_session.headers)
            module.set_token('second')
            self.assertEqual(module.class_task_request.headers['Usertoken'], 'second')
            self.assertNotIn('extra', module.rqs_session.headers)


if __name__ == '__main__':
    unittest.main( )
