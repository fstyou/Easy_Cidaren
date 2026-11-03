import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests import PROJECT_ROOT


spec = importlib.util.spec_from_file_location(
        'packaging_build', PROJECT_ROOT / 'build' / 'build.py'
)
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


class WindowsPackagingTests(unittest.TestCase):
    def test_help_and_argument_errors_are_in_chinese(self):
        script = str(Path(build.__file__))
        for args, expected_code, expected_text in (
                (['--help'], 0, '打包目标：'),
                ([], 2, '请指定打包目标'),
                (['invalid'], 2, '不支持的打包目标'),
                (['--unknown'], 2, '无法识别的参数'),
        ):
            with self.subTest(args = args):
                result = subprocess.run(
                        [sys.executable, '-B', script, *args],
                        capture_output = True, text = True, encoding = 'utf-8', check = False,
                )
                self.assertEqual(result.returncode, expected_code)
                self.assertIn(expected_text, result.stdout + result.stderr)
    
    def test_installer_uses_python_architecture(self):
        for python_platform, arch, inno_arch in (
                ('win-amd64', 'x64', 'x64compatible'),
                ('win-arm64', 'arm64', 'arm64'),
        ):
            with self.subTest(platform = python_platform), tempfile.TemporaryDirectory( ) as temp, \
                    patch.object(build.sysconfig, 'get_platform', return_value = python_platform), \
                    patch.object(build, 'DIST', Path(temp) / 'output'), \
                    patch.object(build, 'PACKAGES', Path(temp) / 'packages'), \
                    patch.object(build, 'require', return_value = 'iscc'), \
                    patch.object(build, 'bundle'), patch.object(build, 'publish'), \
                    patch.object(build, 'run') as run:
                build.windows( )
                command = run.call_args.args[0]
                self.assertIn(f'/DAppArch={arch}', command)
                self.assertIn(f'/DInnoArch={inno_arch}', command)
                self.assertIn(f'/DOutputName=easy-cidaren_{build.VERSION}_windows_{arch}', command)
    
    def test_publish_preserves_other_files_and_replaces_existing_target(self):
        with tempfile.TemporaryDirectory( ) as temp:
            root = Path(temp)
            source = root / 'package'
            source.write_bytes(b'new')
            output = root / 'output'
            output.mkdir( )
            existing = output / 'existing.exe'
            existing.write_bytes(b'unchanged')
            target = output / 'new.dmg'
            with patch.object(build, 'DIST', output), patch.object(build, 'PACKAGES', root / 'packages'):
                build.publish(source, target)
                self.assertEqual({p.name for p in output.iterdir( )}, {'existing.exe', 'new.dmg'})
                source.write_bytes(b'updated')
                build.publish(source, target)
            self.assertEqual(existing.read_bytes( ), b'unchanged')
            self.assertEqual(target.read_bytes( ), b'updated')
    
    def test_unsupported_python_architecture_is_rejected(self):
        with patch.object(build.sysconfig, 'get_platform', return_value = 'win32'):
            with self.assertRaisesRegex(RuntimeError, 'win32'):
                build.windows( )
    
    def test_temporary_files_removed_only_after_success(self):
        for failure in (False, True):
            with self.subTest(failure = failure), tempfile.TemporaryDirectory( ) as temp:
                root = Path(temp)
                temporary = root / 'temp'
                temporary.mkdir( )
                (temporary / 'intermediate').write_text('data', encoding = 'utf-8')
                artifact = root / 'output' / 'app.dmg'
                artifact.parent.mkdir( )
                artifact.write_text('package', encoding = 'utf-8')
                with patch.object(build, 'BUILD', temporary), \
                        patch.object(build.sys, 'argv', ['build.py', 'macos']), \
                        patch.object(build.sys, 'platform', 'darwin'), \
                        patch.object(build, 'macos', side_effect = RuntimeError('失败') if failure else None,
                                     return_value = artifact):
                    if failure:
                        with self.assertRaises(SystemExit):
                            build.main( )
                    else:
                        build.main( )
                self.assertEqual(temporary.exists( ), failure)
                self.assertEqual(artifact.read_text(encoding = 'utf-8'), 'package')
