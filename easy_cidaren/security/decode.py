import base64
import json
from typing import TypedDict

from easy_cidaren.app_logging.config import Log

bs64 = Log("base64")

JV_TWO = {
    '2_1254': [0, 1, 2, 4, 5, 36, 47, 48, 59, 96, 107],
    '2_9214': [0, 1, 2, 4, 5, 6, 7, 48, 49, 66, 149, 150, 284, 374, 375],
    '2_10232': [0, 1, 2, 5, 6, 7, 8, 46, 65, 66, 199, 270, 328, 329],
    '2_10234': [0, 1, 2, 4, 5, 6, 7, 46, 65, 66, 198, 270, 328, 329],
}

class NoiseRule(TypedDict):
    s: int
    n: int


class DecodeConfig(TypedDict):
    uc: list[NoiseRule]
    avg: int
    loc: list[int]


JV_THREE: dict[str, DecodeConfig] = {
    '3_1021': {
        "uc": [{"s": 0, "n": 1}, {"s": 1, "n": 2}, {"s": 33, "n": 1}, {"s": 57, "n": 1}, {"s": 111, "n": 1}],
        "avg": 5, "loc": [1, 3, 2, 0, 4]
    },
    '3_2265': {
        "uc": [{"s": 0, "n": 2}, {"s": 1, "n": 3}, {"s": 33, "n": 1}, {"s": 57, "n": 1}, {"s": 121, "n": 1}],
        "avg": 5, "loc": [3, 1, 0, 4, 2]
    },
    '3_2277': {
        "uc": [{"s": 0, "n": 3}, {"s": 1, "n": 3}, {"s": 32, "n": 2}, {"s": 50, "n": 1}, {"s": 110, "n": 1}],
        "avg": 5, "loc": [3, 1, 0, 4, 2]
    },
}

DEFAULT_JV_TWO = JV_TWO['2_9214']


def _decode_json(data: str) -> dict:
    text = base64.b64decode(data.encode( )).decode( )
    start = text.find('{')
    if start < 0:
        raise ValueError('解码数据中没有 JSON 对象')
    # Some service payloads prepend one extra opening brace.
    if text.startswith('{{', start):
        start += 1
    result, _ = json.JSONDecoder( ).raw_decode(text, start)
    if not isinstance(result, dict):
        raise ValueError('解码结果不是 JSON 对象')
    return result


def strip_noise(d: str, rules) -> str:
    """
    去除混淆
    :param d: 待去除的乱码数据
    :param rules: 乱码规则
    :return:
    """
    if rules and isinstance(rules[0], int):
        chars = list(d)
        for i in sorted(rules, reverse = True):
            if 0 <= i < len(chars):
                del chars[i]
        return ''.join(chars)
    for r in rules:
        s, n = r["s"], r["n"]
        d = (d[:s] if s else "") + d[s + n:]
    return d


def debase64(data: dict | str, jv: str | int | None = 0):
    """
    base64解码
    :param data: 待解码的数据
    :param jv: 乱码版本标识，默认为0
    :return:
    """
    if isinstance(data, dict):
        data = data["data"]
    if not isinstance(data, str):
        raise ValueError('待解码数据必须为字符串')
    
    jv = str(jv or '')
    bs64.logger.debug("开始解码 jv=%s，数据：%s", jv, data, extra = {'file_only': True})
    try:
        return _decode_json(data)
    except (ValueError, UnicodeError):
        if jv in ('', '0'):
            raise
        if jv.startswith("2_") and jv in JV_TWO:
            clean_data = strip_noise(data, JV_TWO[jv])
        elif jv.startswith("3_") and jv in JV_THREE:
            cfg = JV_THREE[jv]
            d = strip_noise(data, cfg["uc"])
            chunk = len(d) // cfg["avg"]
            if chunk == 0:
                raise ValueError('混淆数据长度不足，无法恢复分块')
            pieces = [d[i * chunk:(i + 1) * chunk] for i in range(cfg["avg"])]
            out = "".join(pieces[cfg["loc"].index(i)] for i in range(cfg["avg"]))
            out += d[cfg["avg"] * chunk:]
            clean_data = out
        else:
            clean_data = strip_noise(data, DEFAULT_JV_TWO)
        
        bs64.logger.debug("去除混淆后：%s", clean_data, extra = {'file_only': True})
        return _decode_json(clean_data)
