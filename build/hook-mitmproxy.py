"""Collect mitmdump resources without the standalone web and console frontends."""
from PyInstaller.utils.hooks import collect_all

_excluded = ('mitmproxy.test', 'mitmproxy.tools.web', 'mitmproxy.tools.console')
datas, binaries, hiddenimports = collect_all(
        'mitmproxy', include_py_files = False, exclude_datas = ['test', 'tools/web', 'tools/console'],
        filter_submodules = lambda name: not any(
                name == prefix or name.startswith(prefix + '.') for prefix in _excluded),
)
