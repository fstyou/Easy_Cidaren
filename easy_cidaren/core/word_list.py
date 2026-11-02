from easy_cidaren.logging.config import Log
from easy_cidaren.paths import DATA_DIR
from easy_cidaren.security.decode import debase64
from easy_cidaren.utils.json_store import write_json

logger = Log('word_list')


def handle_word_result(public_info) -> None:
    result = public_info.get_word_list_result
    data = result['data']
    words = (data if isinstance(data, dict) and 'word_list' in data
             else debase64(data, result['jv']))['word_list']
    word_list = [word['word'] for word in words]
    word_dict = {word['word_zh']: word['word'] for word in words}
    # 当前单元词表覆盖 word_list(判词依赖当前单元)
    public_info.word_list = word_list
    # word_dict 跨单元合并(全局词表池: mode 73 前缀单词可能在其他单元词表)
    public_info.word_dict.update(word_dict)
    # 持久化(跨进程累积: 单任务/不同刷题顺序下全局池完整); 词表池自学习关闭时不写入
    if public_info._self_learn_pool:
        try:
            write_json(DATA_DIR / 'word_pool.json', public_info.word_dict)
        except (OSError, TypeError, ValueError) as exc:
            logger.warning("保存词表池失败：%s", exc)


def extract_book_word(public_info):
    public_info.word_list = [d['word'] for d in public_info.get_book_words_data]


def query_word_unit(public_info):
    public_info.get_word_list_result = debase64(public_info.get_word_list_result['data'],
                                                public_info.get_word_list_result['jv'])
    all_unit = {}
    # 创建所有单元字典
    for unit in public_info.all_unit_name:
        all_unit.update({public_info.course_id + ':' + unit: []})
    # 单词分类
    for word_info in public_info.get_word_list_result['word_list']:
        all_unit[public_info.course_id + ":" + word_info['list_id']].append(word_info['word'])
    # 清除无效单元
    all_unit = {key: value for key, value in all_unit.items( ) if value}
    public_info.word_list = all_unit
