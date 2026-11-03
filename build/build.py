"""在当前操作系统上构建应用安装包。"""

import argparse
import importlib.util
import os
import platform
import shutil
import subprocess
import sys
import sysconfig
import tempfile
from pathlib import Path
from typing import NoReturn

ROOT = Path(__file__).resolve( ).parents[1]
sys.path.insert(0, str(ROOT))
from easy_cidaren import __version__

BUILD = ROOT / 'build' / 'temp'
DIST = ROOT / 'build' / 'output'
BUNDLE = BUILD / 'bundle'
PACKAGES = BUILD / 'packages'
NAME = 'EasyCidaren'
VERSION = __version__


def artifact_path(target, architecture, extension):
    return DIST / f'easy-cidaren_{VERSION}_{target}_{architecture}.{extension}'


def machine_architecture( ):
    machine = platform.machine( ).lower( )
    architectures = {'x86_64': 'x64', 'amd64': 'x64', 'arm64': 'arm64', 'aarch64': 'arm64'}
    if machine not in architectures:
        raise RuntimeError(f'不支持的 CPU 架构：{machine}')
    return architectures[machine]


def publish(source, destination):
    DIST.mkdir(parents = True, exist_ok = True)
    PACKAGES.mkdir(parents = True, exist_ok = True)
    temporary = None
    try:
        with source.open('rb') as input_file, tempfile.NamedTemporaryFile(dir = PACKAGES, delete = False) as output:
            temporary = Path(output.name)
            shutil.copyfileobj(input_file, output)
        shutil.copymode(source, temporary)
        temporary.replace(destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok = True)
    return destination


def run(command):
    print('执行命令：', subprocess.list2cmdline([str(part) for part in command]), flush = True)
    subprocess.run([str(part) for part in command], cwd = ROOT, check = True)


def require(command):
    found = shutil.which(command)
    if not found:
        raise RuntimeError(f'缺少构建工具：{command}，请参阅 build/README.md')
    return found


def bundle( ):
    if importlib.util.find_spec('PyInstaller') is None:
        raise RuntimeError('未安装 PyInstaller，请运行：python -m pip install -r build/requirements.txt')
    BUILD.mkdir(parents = True, exist_ok = True)
    command = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--windowed',
               '--name', NAME, '--distpath', BUNDLE, '--workpath', BUILD / 'work',
               '--specpath', BUILD, '--paths', ROOT, '--collect-all', 'spacy',
               '--collect-all', 'mitmproxy', '--collect-all', 'mitmproxy_rs',
               '--hidden-import', 'mitmproxy.tools.main',
               '--add-data', f'{ROOT / "assets"}{os.pathsep}assets',
               '--add-data', f'{ROOT / "data"}{os.pathsep}data',
               '--add-data', f'{ROOT / "easy_cidaren/token_capture/addon.py"}{os.pathsep}easy_cidaren/token_capture',
               '--add-data', f'{ROOT / "LICENSE"}{os.pathsep}.']
    if sys.platform == 'win32':
        command += ['--icon', ROOT / 'assets' / 'icon.ico']
    if sys.platform == 'darwin':
        command += ['--icon', ROOT / 'assets' / 'icon.icns',
                    '--osx-bundle-identifier', 'com.fstyou.easycidaren']
    run([*command, ROOT / 'main.py'])


def windows( ):
    platforms = {'win-amd64': ('x64', 'x64compatible'), 'win-arm64': ('arm64', 'arm64')}
    python_platform = sysconfig.get_platform( ).lower( )
    if python_platform not in platforms:
        raise RuntimeError(f'不支持的 Windows Python 架构：{python_platform}')
    architecture, inno_architecture = platforms[python_platform]
    destination = artifact_path('windows', architecture, 'exe')
    compiler = require('iscc')
    bundle( )
    PACKAGES.mkdir(parents = True, exist_ok = True)
    run([compiler, f'/DAppVersion={VERSION}', f'/DAppSource={BUNDLE / NAME}',
         f'/DOutputDir={PACKAGES}', f'/DAppArch={architecture}',
         f'/DInnoArch={inno_architecture}', f'/DOutputName={destination.stem}',
         ROOT / 'build' / 'windows.iss'])
    return publish(PACKAGES / destination.name, destination)


def macos( ):
    destination = artifact_path('macos', machine_architecture( ), 'dmg')
    hdiutil = require('hdiutil')
    bundle( )
    staging = BUILD / 'dmg'
    if staging.exists( ):
        shutil.rmtree(staging)
    staging.mkdir(parents = True)
    shutil.copytree(BUNDLE / f'{NAME}.app', staging / f'{NAME}.app', symlinks = True)
    (staging / 'Applications').symlink_to('/Applications')
    PACKAGES.mkdir(parents = True, exist_ok = True)
    image = PACKAGES / destination.name
    run([hdiutil, 'create', '-volname', NAME, '-srcfolder', staging, '-ov',
         '-format', 'UDZO', image])
    return publish(image, destination)


def linux( ):
    architecture = machine_architecture( )
    destinations = {kind: artifact_path('linux', architecture, kind) for kind in ('deb', 'rpm')}
    fpm = require('fpm')
    require('dpkg-deb')
    require('rpmbuild')
    bundle( )
    stage = BUILD / 'linux'
    if stage.exists( ):
        shutil.rmtree(stage)
    (stage / 'opt').mkdir(parents = True)
    shutil.copytree(BUNDLE / NAME, stage / 'opt' / 'easy-cidaren', symlinks = True)
    bin_dir = stage / 'usr' / 'bin'
    bin_dir.mkdir(parents = True)
    launcher = bin_dir / 'easy-cidaren'
    launcher.write_text('#!/bin/sh\nexec /opt/easy-cidaren/EasyCidaren "$@"\n', encoding = 'utf-8')
    launcher.chmod(0o755)
    desktop = stage / 'usr' / 'share' / 'applications'
    desktop.mkdir(parents = True)
    icons = stage / 'usr' / 'share' / 'icons' / 'hicolor' / '256x256' / 'apps'
    icons.mkdir(parents = True)
    shutil.copy2(ROOT / 'assets' / 'icon.png', icons / 'easy-cidaren.png')
    (desktop / 'easy-cidaren.desktop').write_text(
            '[Desktop Entry]\nType=Application\nName=Easy Cidaren\nExec=easy-cidaren\nIcon=easy-cidaren\nCategories=Education;\nTerminal=false\n',
            encoding = 'utf-8')
    PACKAGES.mkdir(parents = True, exist_ok = True)
    for kind in ('deb', 'rpm'):
        run([fpm, '-f', '-s', 'dir', '-t', kind, '-n', 'easy-cidaren', '-v', VERSION,
             '--license', 'GPL-3.0-only', '--maintainer', 'Easy Cidaren',
             '--url', 'https://github.com/fstyou/Easy_Cidaren',
             '--description', 'Easy Cidaren desktop application',
             '-p', PACKAGES / destinations[kind].name, '-C', stage, 'opt', 'usr'])
    return [publish(PACKAGES / destination.name, destination) for destination in destinations.values( )]


class ChineseArgumentParser(argparse.ArgumentParser):
    def format_usage(self):
        return super( ).format_usage( ).replace('usage:', '用法：', 1)

    def format_help(self):
        return super( ).format_help( ).replace('usage:', '用法：', 1)

    def error(self, message) -> NoReturn:
        if message.startswith('unrecognized arguments:'):
            message = message.replace('unrecognized arguments:', '无法识别的参数：', 1)
        self.print_usage(sys.stderr)
        self.exit(2, f'{self.prog}：错误：{message}\n')


def main( ):
    parser = ChineseArgumentParser(
            description = '在当前操作系统上构建 Easy Cidaren 安装包。',
            epilog = (
                '打包目标：\n'
                '  windows  生成包含卸载器的 Windows 安装程序（需要 Inno Setup 6）\n'
                '  macos    生成包含应用程序的 macOS DMG（需要 hdiutil）\n'
                '  linux    生成 Linux DEB 和 RPM（需要 fpm、dpkg-deb 和 rpmbuild）\n\n'
                '示例：\n'
                '  python build/build.py windows\n'
                '  python build/build.py macos\n'
                '  python build/build.py linux\n\n'
                '请在目标操作系统和 CPU 架构上运行。\n'
                'Windows ARM64 尚未完成适配。\n'
                '中间文件位于 build/temp/，打包成功后自动删除；产物位于 build/output/。\n'
                '依赖安装及详细说明：build/README.md'
            ),
            formatter_class = argparse.RawDescriptionHelpFormatter,
            add_help = False,
    )
    parser._positionals.title = '位置参数'
    parser._optionals.title = '选项'
    parser.add_argument('target', nargs = '?', metavar = '目标', help = '目标平台：windows、macos 或 linux')
    parser.add_argument('-h', '--help', action = 'help', help = '显示帮助信息并退出')
    target = parser.parse_args( ).target
    targets = {'windows': 'win32', 'macos': 'darwin', 'linux': 'linux'}
    if target is None:
        parser.error('请指定打包目标：windows、macos 或 linux')
    if target not in targets:
        parser.error(f'不支持的打包目标：{target}；请选择 windows、macos 或 linux')
    expected = targets[target]
    if not sys.platform.startswith(expected):
        parser.error(f'{target} 必须在对应的操作系统上构建')
    try:
        result = {'windows': windows, 'macos': macos, 'linux': linux}[target]( )
    except subprocess.CalledProcessError as exc:
        parser.exit(1, f'打包失败：外部命令退出，状态码为 {exc.returncode}。\n')
    except (RuntimeError, OSError) as exc:
        parser.exit(1, f'打包失败：{exc}\n')
    for path in result if isinstance(result, list) else [result]:
        print(f'打包完成：{path}')
    try:
        if BUILD.exists( ):
            shutil.rmtree(BUILD)
    except OSError as exc:
        parser.exit(1, f'产物已生成，但清理临时目录失败：{exc}\n')


if __name__ == '__main__':
    main( )
