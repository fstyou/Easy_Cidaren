import copy
import json
import threading

from easy_cidaren.logging.config import Log
from easy_cidaren.paths import DATA_DIR
from easy_cidaren.utils.json_store import write_json

answer_lib_logger = Log('answer_lib')

_lock = threading.Lock( )
_lib = None


def load_lib(force = False):
    global _lib
    if _lib is None or force:
        path = DATA_DIR / 'answer_lib.json'
        if path.exists( ):
            try:
                with open(path, 'r', encoding = 'utf-8') as f:
                    _lib = json.load(f)
            except (OSError, json.JSONDecodeError) as e:
                answer_lib_logger.error(f"加载答案库失败: {e}")
                raise
        else:
            _lib = {}
    return _lib


def lookup(word_zh):
    if not word_zh:
        return None
    return load_lib( ).get(word_zh) or None


WORD_KEY = '_word_answers'


def _save_lib(lib):
    try:
        write_json(DATA_DIR / 'answer_lib.json', lib, indent = 2)
        return True
    except (OSError, TypeError, ValueError) as e:
        answer_lib_logger.error(f"保存答案库失败: {e}")
        return False


def lookup_word(word_zh):
    """单词级答案(mode 42 选项单词/同义变体), 与短语答案分开存储"""
    if not word_zh:
        return None
    return load_lib( ).get(WORD_KEY, {}).get(word_zh) or None


def _add_answers(word_zh, answers, *, word_level):
    global _lib
    if not word_zh or not answers:
        return
    values = [value for value in answers if isinstance(value, str) and value]
    if not values:
        return
    with _lock:
        lib = copy.deepcopy(load_lib( ))
        mapping = lib.setdefault(WORD_KEY, {}) if word_level else lib
        previous = mapping.setdefault(word_zh, [])
        added = False
        for value in values:
            if value not in previous:
                previous.append(value)
                added = True
        if added:
            if _save_lib(lib):
                _lib = lib


def add_word_answer(word_zh, words):
    _add_answers(word_zh, words, word_level = True)


def add_answer(word_zh, corrects):
    _add_answers(word_zh, corrects, word_level = False)
