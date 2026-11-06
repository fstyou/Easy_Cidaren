"""Collect spaCy runtime resources without its bundled test suite."""
from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = collect_all(
        'spacy', include_py_files = False,
        exclude_datas = ['tests', '**/*.pyx', '**/*.pxd', '**/*.pxi', '**/*.pyi'],
        filter_submodules = lambda name: name != 'spacy.tests' and not name.startswith('spacy.tests.'),
)
