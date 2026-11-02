import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


class SessionTests(unittest.TestCase):
    def test_login_sessions_have_independent_headers(self):
        requests = types.ModuleType('requests')
        requests.exceptions = types.SimpleNamespace( )
        requests.session = lambda: types.SimpleNamespace(headers = {})
        modules = {
            'requests': requests,
            'easy_cidaren.core.public_info': types.SimpleNamespace(
                    PublicInfo = lambda: types.SimpleNamespace(accept_encoding = 'gzip')),
            'easy_cidaren.security.signing': types.SimpleNamespace(encrypt_md5 = lambda value: 'signature'),
        }
        path = Path(__file__).resolve( ).parents[1] / 'easy_cidaren' / 'api' / 'sessions.py'
        with patch.dict(sys.modules, modules):
            spec = importlib.util.spec_from_file_location('test_sessions_module', path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            module.set_token('first')
            module.rqs_session.headers['extra'] = 'value'
            self.assertNotIn('extra', module.class_task_request.headers)
            self.assertNotIn('Usertoken', module.headers)
            self.assertNotIn('Content-Length', module.rqs2_session.headers)
            module.set_token('second')
            self.assertEqual(module.class_task_request.headers['Usertoken'], 'second')
            self.assertNotIn('extra', module.rqs_session.headers)


if __name__ == '__main__':
    unittest.main( )
