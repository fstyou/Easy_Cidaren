import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


class CourseTests(unittest.TestCase):
    def test_word_query_passes_word_as_parameter(self):
        import easy_cidaren.api as api_package
        response = types.SimpleNamespace(json = lambda: {'data': {'word_mean': {'meaning': '<span>test</span>'}}})
        session = types.SimpleNamespace(get = Mock(return_value = response))
        sessions = types.ModuleType('easy_cidaren.api.sessions')
        sessions.rqs_session = session
        modules = {
            'easy_cidaren.api.sessions': sessions,
            'easy_cidaren.api.response': types.SimpleNamespace(handle_response = Mock( )),
            'easy_cidaren.logging.config': types.SimpleNamespace(
                    Log = lambda name: types.SimpleNamespace(logger = Mock( ))),
            'easy_cidaren.utils.helpers': types.SimpleNamespace(create_timestamp = lambda: 123),
        }
        path = Path(__file__).resolve( ).parents[1] / 'easy_cidaren' / 'api' / 'courses.py'
        with patch.dict(sys.modules, modules), patch.object(api_package, 'sessions', sessions, create = True):
            spec = importlib.util.spec_from_file_location('test_courses_module', path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self.assertEqual(module.use_api_get_prototype('a&b'), 'test')
            self.assertEqual(session.get.call_args.kwargs['params']['word'], 'a&b')
            self.assertEqual(session.get.call_args.kwargs['params']['timestamp'], 123)


if __name__ == '__main__':
    unittest.main( )
