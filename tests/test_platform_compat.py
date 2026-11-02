import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class FakeLog:
    def __init__(self, *args):
        self.logger = self

    def __getattr__(self, name):
        return lambda *args, **kwargs: None


class PlatformCompatibilityTests(unittest.TestCase):
    def test_answer_library_does_not_depend_on_working_directory(self):
        with patch.dict(sys.modules, {"log.log": types.SimpleNamespace(Log=FakeLog)}):
            from util.answer_lib import _lib_path
            with tempfile.TemporaryDirectory() as directory:
                previous = os.getcwd()
                try:
                    os.chdir(directory)
                    self.assertEqual(Path(_lib_path()), ROOT / "config" / "answer_lib.json")
                finally:
                    os.chdir(previous)

    def test_finds_executable_beside_interpreter_without_path(self):
        from util.executables import find_mitmdump
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / ("mitmdump.exe" if os.name == "nt" else "mitmdump")
            executable.touch()
            with patch.object(sys, "executable", str(Path(directory) / "python")):
                with patch.dict(os.environ, {"PATH": ""}):
                    self.assertEqual(find_mitmdump(), str(executable))

    def test_linux_proxy_does_not_claim_to_configure_other_processes(self):
        path = ROOT / "get token" / "fetch_token" / "proxy_manager.py"
        with patch.dict(sys.modules, {"log.log": types.SimpleNamespace(Log=FakeLog)}):
            spec = importlib.util.spec_from_file_location("test_proxy_manager", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            manager = module.ProxyManager()
            manager.os = "Linux"
            original = dict(os.environ)
            manager.enable_proxy()
            manager.disable_proxy()
            self.assertEqual(dict(os.environ), original)


if __name__ == "__main__":
    unittest.main()
