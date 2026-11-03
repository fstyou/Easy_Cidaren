import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from tests.module_loader import load_module

ROOT = Path(__file__).resolve( ).parents[1]
sys.path.insert(0, str(ROOT))


class FakeLog:
    def __init__(self, *args):
        self.logger = self
    
    def __getattr__(self, name):
        return lambda *args, **kwargs: None


class PlatformCompatibilityTests(unittest.TestCase):
    def test_certificate_startup_failure_is_reported(self):
        from easy_cidaren.token_capture.service import TokenCaptureService
        with tempfile.TemporaryDirectory( ) as directory:
            service = TokenCaptureService(directory)
            service.mitm_process = Mock( )
            service.mitm_process.poll.return_value = 1
            with patch('easy_cidaren.token_capture.service.Path.home', return_value = Path(directory)):
                with self.assertRaisesRegex(RuntimeError, '生成证书前已退出'):
                    service._ensure_mitm_cert_ready( )
                service.mitm_process.poll.return_value = None
                with patch('easy_cidaren.token_capture.service.time.time', side_effect = [0, 16]):
                    with self.assertRaisesRegex(RuntimeError, '证书生成超时'):
                        service._ensure_mitm_cert_ready( )

    def test_answer_library_does_not_depend_on_working_directory(self):
        from easy_cidaren.paths import DATA_DIR
        with tempfile.TemporaryDirectory( ) as directory:
            previous = os.getcwd( )
            try:
                os.chdir(directory)
                self.assertEqual(DATA_DIR / "answer_lib.json", ROOT / "data" / "answer_lib.json")
            finally:
                os.chdir(previous)
    
    def test_finds_executable_beside_interpreter_without_path(self):
        from easy_cidaren.utils.executables import find_mitmdump
        with tempfile.TemporaryDirectory( ) as directory:
            executable = Path(directory) / ("mitmdump.exe" if os.name == "nt" else "mitmdump")
            executable.touch( )
            with patch.object(sys, "executable", str(Path(directory) / "python")):
                with patch.dict(os.environ, {"PATH": ""}):
                    self.assertEqual(find_mitmdump( ), str(executable))
    
    def test_linux_proxy_does_not_claim_to_configure_other_processes(self):
        path = ROOT / "easy_cidaren" / "token_capture" / "proxy_manager.py"
        with patch.dict(sys.modules, {"easy_cidaren.app_logging.config": types.SimpleNamespace(Log = FakeLog)}):
            module = load_module("test_proxy_manager", path)
            manager = module.ProxyManager( )
            manager.os = "Linux"
            original = dict(os.environ)
            manager.enable_proxy( )
            manager.disable_proxy( )
            self.assertEqual(dict(os.environ), original)
    
    def test_proxy_restore_reports_failures_after_attempting_both_protocols(self):
        path = ROOT / 'easy_cidaren' / 'token_capture' / 'proxy_manager.py'
        with patch.dict(sys.modules, {'easy_cidaren.app_logging.config': types.SimpleNamespace(Log = FakeLog)}):
            module = load_module('test_proxy_restore', path)
            manager = module.ProxyManager( )
            manager.os = 'Darwin'
            manager.original_settings = {'Wi-Fi': {
                'web_enabled': False, 'web_host': '', 'web_port': '',
                'secure_enabled': False, 'secure_host': '', 'secure_port': '',
            }}
            error = module.subprocess.CalledProcessError(1, 'networksetup')
            with patch.object(module.subprocess, 'run', side_effect = [error, None]) as run:
                with self.assertRaisesRegex(RuntimeError, '恢复 macOS 代理失败'):
                    manager.disable_proxy( )
                self.assertEqual(run.call_count, 2)
            manager.os = 'Windows'
            manager.original_settings = {'windows': {'enabled': False, 'server': '', 'override': ''}}
            with patch.object(manager, '_set_windows_proxy_settings', return_value = False):
                with self.assertRaisesRegex(RuntimeError, '恢复 Windows 代理失败'):
                    manager.disable_proxy( )
    
    def test_capture_uses_packaged_addon_and_existing_data_directory(self):
        class FakeProxy:
            def enable_proxy(self, **kwargs):
                pass
            
            def disable_proxy(self):
                pass
        
        class FakeProcess:
            pid = 123
            returncode = None
            
            def poll(self):
                return self.returncode
            
            def terminate(self):
                self.returncode = 0
            
            def wait(self, timeout = None):
                return self.returncode
        
        modules = {
            'easy_cidaren.app_logging.config': types.SimpleNamespace(Log = FakeLog),
            'easy_cidaren.token_capture.proxy_manager': types.SimpleNamespace(ProxyManager = FakeProxy),
        }
        path = ROOT / 'easy_cidaren' / 'token_capture' / 'service.py'
        with patch.dict(sys.modules, modules), tempfile.TemporaryDirectory( ) as directory:
            module = load_module('test_capture_service', path)
            capture_dir = Path(directory) / 'runtime' / 'token_capture'
            capture_dir.mkdir(parents = True)
            (capture_dir / 'last_token.txt').write_text('previous-token', encoding = 'utf-8')
            service = module.TokenCaptureService(str(capture_dir))
            popen_args = {}
            previous_token = 'previous-token'
            
            def launch(args, **kwargs):
                popen_args.update(args = args, **kwargs)
                self.assertEqual((capture_dir / 'last_token.txt').read_text(encoding = 'utf-8'), previous_token)
                new_file = capture_dir / 'new-token'
                new_file.write_text('test-token', encoding = 'utf-8')
                os.replace(new_file, capture_dir / 'last_token.txt')
                return FakeProcess( )
            
            with patch.object(module, 'find_mitmdump', return_value = 'mitmdump'), \
                    patch.object(service, '_is_port_in_use', return_value = False), \
                    patch.object(service, '_ensure_mitm_cert_ready'), \
                    patch.object(module.subprocess, 'Popen', side_effect = launch):
                self.assertEqual(service.start_capture( ), 'test-token')
                previous_token = 'test-token'
                service = module.TokenCaptureService(str(capture_dir))
                with patch.object(service, '_is_port_in_use', return_value = False), \
                        patch.object(service, '_ensure_mitm_cert_ready'):
                    self.assertEqual(service.start_capture( ), 'test-token')
            self.assertEqual(popen_args['env']['EASY_CIDAREN_TOKEN_FILE'],
                             str((capture_dir / 'last_token.txt').resolve( )))
            self.assertEqual(Path(popen_args['args'][2]), path.parent / 'addon.py')
            host_index = popen_args['args'].index('--listen-host')
            self.assertEqual(popen_args['args'][host_index + 1], '127.0.0.1')
            self.assertEqual((capture_dir / 'last_token.txt').read_text(encoding = 'utf-8'), 'test-token')
            service = module.TokenCaptureService(str(capture_dir))
            stopped_process = FakeProcess( )
            stopped_process.returncode = 1
            with patch.object(module, 'find_mitmdump', return_value = 'mitmdump'), \
                    patch.object(service, '_is_port_in_use', return_value = False), \
                    patch.object(service, '_ensure_mitm_cert_ready'), \
                    patch.object(module.subprocess, 'Popen', return_value = stopped_process):
                self.assertIsNone(service.start_capture( ))
            self.assertEqual((capture_dir / 'last_token.txt').read_text(encoding = 'utf-8'), 'test-token')
    
    def test_task_api_response_handler_after_package_move(self):
        import easy_cidaren.api as api_package
        modules = {
            'easy_cidaren.app_logging.config': types.SimpleNamespace(Log = FakeLog),
            'easy_cidaren.api.sessions': types.ModuleType('easy_cidaren.api.sessions'),
            'easy_cidaren.security.decode': types.SimpleNamespace(debase64 = lambda *args: None, JV_TWO = (),
                                                                  JV_THREE = ()),
            'easy_cidaren.security.signing': types.SimpleNamespace(encrypt_md5 = lambda value: value),
            'easy_cidaren.core.public_info': types.SimpleNamespace(PublicInfo = type('PublicInfo', (), {})),
            'easy_cidaren.utils.helpers': types.SimpleNamespace(create_timestamp = lambda: 0),
        }
        path = ROOT / 'easy_cidaren' / 'api' / 'tasks.py'
        with patch.dict(sys.modules, modules), \
                patch.object(api_package, 'sessions', modules['easy_cidaren.api.sessions'], create = True):
            module = load_module('test_tasks_module', path)
            response = types.SimpleNamespace(json = lambda: {'code': 1}, text = 'ok')
            module.handle_response(response)
            unknown = types.SimpleNamespace(json = lambda: {'jv': 'unknown'})
            known = types.SimpleNamespace(json = lambda: {'jv': '0'})
            request = Mock(side_effect = [unknown, known])
            with patch.object(module.time, 'sleep'):
                self.assertIs(module.request_with_known_jv(request, '/test', params = {'x': 1}), known)
            self.assertEqual(request.call_count, 2)
            self.assertEqual(request.call_args.kwargs, {'params': {'x': 1}, 'timeout': 30})
            request = Mock(return_value = unknown)
            with patch.object(module.time, 'sleep'), self.assertRaises(ValueError):
                module.request_with_known_jv(request, '/test')
            self.assertEqual(request.call_count, 5)
            module.PublicInfo.task_type = 'StudyTask'
            modules['easy_cidaren.api.sessions'].rqs2_session = types.SimpleNamespace(post = Mock( ))
            result = {'answer_result': 1, 'topic_code': 'next'}
            response = types.SimpleNamespace(json = lambda: {'data': 'encoded', 'jv': '0'})
            info = types.SimpleNamespace(topic_code = 'current', right_count = 0)
            with patch.object(module, 'request_with_known_jv', return_value = response), \
                    patch.object(module, 'handle_response'), \
                    patch.object(module, 'debase64', return_value = result):
                self.assertIs(module.submit_result(info, 'answer'), result)
            self.assertEqual((info.topic_code, info.right_count), ('current', 0))


if __name__ == "__main__":
    unittest.main( )
