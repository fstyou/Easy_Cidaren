import copy
import json
import threading

from easy_cidaren.app_logging.config import get_logger
from easy_cidaren.paths import DATA_DIR
from easy_cidaren.utils.json_store import write_json

answer_lib_logger = get_logger('answer_lib')

_lock = threading.Lock( )
_lib = None
WORD_KEY = '_word_answers'


class AnswerLibraryError(Exception):
    """The local answer library cannot safely be used or updated."""


def _validate_answers(mapping):
    if not isinstance(mapping, dict) or any(
            not isinstance(key, str) or not isinstance(values, list)
            or any(not isinstance(value, str) for value in values)
            for key, values in mapping.items( )):
        raise AnswerLibraryError('本地答案库格式错误：答案必须是字符串列表，请检查 answer_lib.json')


def load_lib( ):
    global _lib
    if _lib is None:
        path = DATA_DIR / 'answer_lib.json'
        try:
            with path.open(encoding = 'utf-8') as stream:
                lib = json.load(stream)
        except FileNotFoundError:
            lib = {}
        except (OSError, ValueError) as exc:
            raise AnswerLibraryError('无法读取本地答案库，请检查 answer_lib.json') from exc
        if not isinstance(lib, dict):
            raise AnswerLibraryError('本地答案库格式错误：顶层必须是对象，请检查 answer_lib.json')
        _validate_answers({key: value for key, value in lib.items( ) if key != WORD_KEY})
        _validate_answers(lib.get(WORD_KEY, {}))
        _lib = lib
    return _lib


def lookup(word_zh):
    if not word_zh:
        return None
    lib = _available_lib( )
    if lib is None:
        return None
    return lib.get(word_zh) or None


def _available_lib( ):
    try:
        return load_lib( )
    except AnswerLibraryError as exc:
        answer_lib_logger.warning('跳过本地答案库读写，继续答题：%s', exc)
        return None


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
    lib = _available_lib( )
    if lib is None:
        return None
    return lib.get(WORD_KEY, {}).get(word_zh) or None


def _add_answers(word_zh, answers, *, word_level):
    global _lib
    if not word_zh or not answers:
        return
    if isinstance(answers, str):
        answers = [answers]
    if not isinstance(answers, list):
        return
    values = [value for value in answers if isinstance(value, str) and value]
    if not values:
        return
    with _lock:
        current = _available_lib( )
        if current is None:
            return
        mapping = current.get(WORD_KEY, {}) if word_level else current
        previous = mapping.get(word_zh, [])
        additions = [value for value in dict.fromkeys(values) if value not in previous]
        if not additions:
            return
        lib = copy.deepcopy(current)
        mapping = lib.setdefault(WORD_KEY, {}) if word_level else lib
        mapping[word_zh] = previous + additions
        if _save_lib(lib):
            _lib = lib


def add_word_answer(word_zh, words):
    _add_answers(word_zh, words, word_level = True)


def add_answer(word_zh, corrects):
    _add_answers(word_zh, corrects, word_level = False)
