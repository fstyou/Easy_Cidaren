import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from build import build
from tests import PROJECT_ROOT


class BuildTests(unittest.TestCase):
    def test_help_and_argument_errors_are_in_chinese(self):
        script = str(PROJECT_ROOT / 'build' / 'build.py')
        for args, expected_code, expected_text in (
                (['--help'], 0, '打包目标：'),
                ([], 2, '请指定打包目标'),
                (['invalid'], 2, '不支持的打包目标'),
                (['--unknown'], 2, '无法识别的参数'),
        ):
            with self.subTest(args = args):
                result = subprocess.run(
                        [sys.executable, '-B', script, *args],
                        capture_output = True, text = True, encoding = 'utf-8',
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
    
    def test_failed_publish_keeps_existing_artifact(self):
        with tempfile.TemporaryDirectory( ) as temp:
            root = Path(temp)
            target = root / 'existing.deb'
            target.write_bytes(b'previous')
            with patch.object(build, 'DIST', root), self.assertRaises(FileNotFoundError):
                build.publish(root / 'missing.deb', target)
            self.assertEqual(target.read_bytes( ), b'previous')
    
    def test_linux_build_produces_only_deb_and_rpm_for_each_architecture(self):
        for arch, deb_arch, rpm_arch in (('x64', 'amd64', 'x86_64'), ('arm64', 'arm64', 'aarch64')):
            with self.subTest(arch = arch), tempfile.TemporaryDirectory( ) as temp:
                root = Path(temp)
                bundle = root / 'bundle'
                (bundle / build.NAME).mkdir(parents = True)
                (bundle / build.NAME / build.NAME).write_bytes(b'executable')
                output = root / 'output'
                output.mkdir( )
                existing = output / 'existing.exe'
                existing.write_bytes(b'unchanged')
                commands = []
                
                def create_package(command):
                    commands.append(command)
                    package = Path(command[command.index('-p') + 1])
                    package.write_bytes(b'package')
                
                with patch.object(build, 'BUILD', root / 'temp'), \
                        patch.object(build, 'DIST', output), patch.object(build, 'BUNDLE', bundle), \
                        patch.object(build, 'PACKAGES', root / 'temp' / 'packages'), \
                        patch.object(build, 'machine_architecture', return_value = arch), \
                        patch.object(build, 'require', side_effect = lambda command: command), \
                        patch.object(build, 'bundle'), patch.object(build, 'run', side_effect = create_package):
                    packages = build.linux( )
                self.assertEqual([command[command.index('-a') + 1] for command in commands], [deb_arch, rpm_arch])
                self.assertEqual({path.name for path in output.iterdir( )}, {
                    'existing.exe', f'easy-cidaren_{build.VERSION}_linux_{arch}.deb',
                    f'easy-cidaren_{build.VERSION}_linux_{arch}.rpm',
                })
                self.assertEqual([path.read_bytes( ) for path in packages], [b'package', b'package'])
                self.assertEqual(existing.read_bytes( ), b'unchanged')
    
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
