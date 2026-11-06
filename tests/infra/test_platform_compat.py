import hashlib
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

from easy_cidaren.token_capture import proxy_manager
from easy_cidaren.token_capture import service as capture_service
from easy_cidaren.token_capture.proxy_manager import ProxyManager
from tests import PROJECT_ROOT

class PlatformCompatibilityTests(unittest.TestCase):
    def test_registry_handles_close_when_reading_or_writing_fails(self):
        for operation in ('read', 'write'):
            with self.subTest(operation = operation):
                registry = MagicMock( )
                key = registry.OpenKey.return_value
                registry.QueryValueEx.side_effect = OSError('read failed')
                registry.SetValueEx.side_effect = OSError('write failed')
                with patch.object(proxy_manager, 'winreg', registry, create = True):
                    if operation == 'read':
                        self.assertIsNone(ProxyManager._get_windows_proxy_settings( ))
                    else:
                        self.assertFalse(ProxyManager._set_windows_proxy_settings(True))
                key.__exit__.assert_called_once( )

    def test_windows_certificate_checks_exact_certificate_and_reports_import_errors(self):
        manager = ProxyManager( )
        with tempfile.TemporaryDirectory( ) as directory:
            cert = Path(directory) / '.mitmproxy' / 'mitmproxy-ca-cert.cer'
            cert.parent.mkdir( )
            cert.write_bytes(b'example-certificate')
            fingerprint = hashlib.sha1(b'example-certificate').hexdigest( ).upper( )
            with patch('easy_cidaren.token_capture.proxy_manager.Path.home', return_value = Path(directory)), \
                    patch.object(manager, '_windows_store_has_cert', return_value = False) as has_cert, \
                    patch('easy_cidaren.token_capture.proxy_manager.subprocess.run',
                          side_effect = OSError('certutil unavailable')):
                with self.assertRaisesRegex(RuntimeError, '导入 mitmproxy 证书'):
                    manager.ensure_windows_mitm_cert( )
                has_cert.assert_called_once_with('Root', fingerprint)

    def test_macos_proxy_is_not_changed_when_original_settings_cannot_be_restored(self):
        manager = ProxyManager( )
        manager.os = 'Darwin'
        valid = 'Enabled: Yes\nServer: proxy.example\nPort: 8080\nAuthenticated Proxy Enabled: 0\n'
        for invalid in ('unexpected output',
                        'Enabled: Yes\nServer: \nPort: 0\nAuthenticated Proxy Enabled: 0\n',
                        'Enabled: Yes\nServer: \nPort: 0\n'):
            with self.subTest(output = invalid), \
                    patch.object(manager, '_get_network_services', return_value = ['Wi-Fi']), \
                    patch('easy_cidaren.token_capture.proxy_manager.subprocess.check_output',
                          side_effect = [valid, invalid]), \
                    patch('easy_cidaren.token_capture.proxy_manager.subprocess.run') as run:
                with self.assertRaisesRegex(RuntimeError, '无法读取 macOS 网络代理设置'):
                    manager.enable_proxy( )
                run.assert_not_called( )
                self.assertEqual(manager.original_settings, {})

    def test_macos_proxy_settings_include_enabled_and_disabled_states(self):
        enabled = 'Enabled: Yes\nServer: proxy.example\nPort: 8080\nAuthenticated Proxy Enabled: 0\n'
        disabled = 'Enabled: No\nServer: \nPort: 0\nAuthenticated Proxy Enabled: 0\n'
        with patch('easy_cidaren.token_capture.proxy_manager.subprocess.check_output',
                   side_effect = [enabled, disabled]):
            settings = ProxyManager._get_proxy_info('Wi-Fi')
        self.assertEqual(settings, {'web_enabled': True, 'web_host': 'proxy.example', 'web_port': '8080',
                                    'secure_enabled': False, 'secure_host': '', 'secure_port': '0'})

    def test_macos_authentication_marker_does_not_block_capture_or_restore(self):
        for authentication in ('', 'Authenticated Proxy Enabled: 0\n', 'Authenticated Proxy Enabled: 1\n'):
            with self.subTest(authentication = authentication):
                manager = ProxyManager( )
                manager.os = 'Darwin'
                output = 'Enabled: Yes\nServer: 127.0.0.1\nPort: 7890\n' + authentication
                with patch.object(manager, '_get_network_services', return_value = ['Wi-Fi']), \
                        patch('easy_cidaren.token_capture.proxy_manager.subprocess.check_output',
                              return_value = output), \
                        patch('easy_cidaren.token_capture.proxy_manager.subprocess.run') as run:
                    manager.enable_proxy( )
                    manager.disable_proxy( )
                self.assertEqual([call.args[0] for call in run.call_args_list], [
                    ['networksetup', '-setwebproxy', 'Wi-Fi', '127.0.0.1', '8888'],
                    ['networksetup', '-setsecurewebproxy', 'Wi-Fi', '127.0.0.1', '8888'],
                    ['networksetup', '-setwebproxy', 'Wi-Fi', '127.0.0.1', '7890'],
                    ['networksetup', '-setsecurewebproxy', 'Wi-Fi', '127.0.0.1', '7890'],
                ])

    def test_linux_capture_cleanup_emits_typed_restore_notice(self):
        from easy_cidaren.token_capture.service import CaptureStatus, TokenCaptureService
        service = TokenCaptureService('unused')
        service.proxy_manager = Mock( )
        service._proxy_attempted = True
        callback = Mock( )
        with patch('easy_cidaren.token_capture.service.sys.platform', 'linux'):
            service.cleanup(callback)
        callback.assert_called_once( )
        self.assertIs(callback.call_args.args[0], CaptureStatus.RESTORE_PROXY)
        self.assertTrue(callback.call_args.args[1])

    def test_capture_cleanup_does_not_restore_proxy_before_it_was_touched(self):
        from easy_cidaren.token_capture.service import TokenCaptureService
        service = TokenCaptureService('unused')
        service.proxy_manager = Mock( )
        callback = Mock( )
        service.cleanup(callback)
        service.proxy_manager.disable_proxy.assert_not_called( )
        callback.assert_not_called( )

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
                with patch('easy_cidaren.token_capture.service.time.monotonic', side_effect = [0, 16]):
                    with self.assertRaisesRegex(RuntimeError, '证书生成超时'):
                        service._ensure_mitm_cert_ready( )
    
    def test_windows_certificate_import_failure_allows_manual_trust(self):
        from easy_cidaren.token_capture.service import TokenCaptureService
        with tempfile.TemporaryDirectory( ) as directory:
            cert = Path(directory) / '.mitmproxy' / 'mitmproxy-ca-cert.cer'
            cert.parent.mkdir( )
            cert.write_bytes(b'certificate')
            service = TokenCaptureService(directory)
            service.proxy_manager = Mock( )
            service.proxy_manager.ensure_windows_mitm_cert.side_effect = RuntimeError('import failed')
            with patch('easy_cidaren.token_capture.service.Path.home', return_value = Path(directory)), \
                    patch('easy_cidaren.token_capture.service.sys.platform', 'win32'):
                callback = Mock( )
                service._ensure_mitm_cert_ready(callback)
                self.assertEqual(callback.call_args.args[0], capture_service.CaptureStatus.CERT_TRUST)
                self.assertIn('手动信任', callback.call_args.args[1])

    def test_answer_library_does_not_depend_on_working_directory(self):
        from easy_cidaren.paths import DATA_DIR
        with tempfile.TemporaryDirectory( ) as directory:
            previous = os.getcwd( )
            try:
                os.chdir(directory)
                self.assertEqual(DATA_DIR / "answer_lib.json", PROJECT_ROOT / "data" / "answer_lib.json")
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
        manager = ProxyManager( )
        manager.os = 'Linux'
        original = dict(os.environ)
        manager.enable_proxy( )
        manager.disable_proxy( )
        self.assertEqual(dict(os.environ), original)
    
    def test_proxy_restore_reports_failures_after_attempting_both_protocols(self):
        manager = ProxyManager( )
        manager.os = 'Darwin'
        manager.original_settings = {'Wi-Fi': {
            'web_enabled': False, 'web_host': '', 'web_port': '',
            'secure_enabled': False, 'secure_host': '', 'secure_port': '',
        }}
        error = subprocess.CalledProcessError(1, 'networksetup')
        with patch('easy_cidaren.token_capture.proxy_manager.subprocess.run', side_effect = [error, None]) as run:
            with self.assertRaisesRegex(RuntimeError, '恢复 macOS 代理失败'):
                manager.disable_proxy( )
            self.assertEqual(run.call_count, 2)
        manager.os = 'Windows'
        manager.original_settings = {'windows': {'enabled': False, 'server': '', 'override': ''}}
        with patch.object(manager, '_set_windows_proxy_settings', return_value = False):
            with self.assertRaisesRegex(RuntimeError, '恢复 Windows 代理失败'):
                manager.disable_proxy( )
    
    def test_capture_uses_packaged_addon_and_existing_data_directory(self):
        class FakeProcess:
            pid = 123
            returncode = None
            
            def poll(self):
                return self.returncode
            
            def terminate(self):
                self.returncode = 0
            
            def wait(self, timeout = None):
                return self.returncode
        
        path = PROJECT_ROOT / 'easy_cidaren' / 'token_capture' / 'service.py'
        with tempfile.TemporaryDirectory( ) as directory, patch('easy_cidaren.token_capture.service.ProxyManager'):
            capture_dir = Path(directory) / 'runtime' / 'token_capture'
            capture_dir.mkdir(parents = True)
            (capture_dir / 'last_token.txt').write_text('previous-token', encoding = 'utf-8')
            service = capture_service.TokenCaptureService(str(capture_dir))
            popen_args = {}
            previous_token = 'previous-token'
            
            def launch(args, **kwargs):
                popen_args.update(args = args, **kwargs)
                self.assertEqual((capture_dir / 'last_token.txt').read_text(encoding = 'utf-8'), previous_token)
                new_file = capture_dir / 'new-token'
                new_file.write_text('test-token', encoding = 'utf-8')
                os.replace(new_file, capture_dir / 'last_token.txt')
                return FakeProcess( )
            
            with patch('easy_cidaren.token_capture.service.find_mitmdump', return_value = 'mitmdump'), \
                    patch.object(service, '_is_port_in_use', return_value = False), \
                    patch.object(service, '_ensure_mitm_cert_ready'), \
                    patch.object(capture_service.subprocess, 'Popen', side_effect = launch):
                self.assertEqual(service.start_capture( ), 'test-token')
                previous_token = 'test-token'
                service = capture_service.TokenCaptureService(str(capture_dir))
                with patch.object(service, '_is_port_in_use', return_value = False), \
                        patch.object(service, '_ensure_mitm_cert_ready'):
                    self.assertEqual(service.start_capture( ), 'test-token')
            self.assertEqual(popen_args['env']['EASY_CIDAREN_TOKEN_FILE'],
                             str((capture_dir / 'last_token.txt').resolve( )))
            self.assertEqual(Path(popen_args['args'][2]), path.parent / 'addon.py')
            host_index = popen_args['args'].index('--listen-host')
            self.assertEqual(popen_args['args'][host_index + 1], '127.0.0.1')
            self.assertEqual((capture_dir / 'last_token.txt').read_text(encoding = 'utf-8'), 'test-token')
            service = capture_service.TokenCaptureService(str(capture_dir))
            stopped_process = FakeProcess( )
            stopped_process.returncode = 1
            with patch('easy_cidaren.token_capture.service.find_mitmdump', return_value = 'mitmdump'), \
                    patch.object(service, '_is_port_in_use', return_value = False), \
                    patch.object(service, '_ensure_mitm_cert_ready'), \
                    patch.object(capture_service.subprocess, 'Popen', return_value = stopped_process):
                self.assertIsNone(service.start_capture( ))
            self.assertEqual((capture_dir / 'last_token.txt').read_text(encoding = 'utf-8'), 'test-token')


if __name__ == "__main__":
    unittest.main( )
