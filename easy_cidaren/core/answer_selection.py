import random
import re

from easy_cidaren.api.tasks import query_word
from easy_cidaren.app_logging.config import Log
from easy_cidaren.utils.word_revert import word_revert

# log module
select_module = Log("select_mean")


#
def handle_query_word_mean(public_info) -> None:
    means = []
    if public_info.word_query_result.get('options'):
        for mean in public_info.word_query_result['options']:
            means.append(re.sub("（.*）", "", mean['content']['mean']))
    else:
        for mean in public_info.word_query_result['means']:
            means.append(' '.join(mean['mean']))
    select_module.logger.debug(f"提取到正确选项：{means}")
    public_info.word_means = means


# extract options
def filler_option(public_info) -> list:
    """
    提取题目中返回的选项以及排序优化
    :param public_info:
    :return:
    """
    # 试题选项
    options = []
    source = []
    # 填充选项
    for option_info in public_info.exam["options"]:
        option = option_info['content']
        source.append(option)
        if option in public_info.word_list:
            options.insert(0, option)
        else:
            options.append(option)
    public_info.source_option = source
    select_module.logger.debug(f"提取到题目选项{options}")
    return options


def select_mean(public_info) -> int:
    """
    英译汉 选择匹配的意思
    :param public_info:
    :return: 选择的匹配的选项
    """
    options = filler_option(public_info)
    # 匹配选项
    for index, option in enumerate(options):
        for mean in public_info.word_means:
            # 选项顺序混乱，重排序
            if sorted(option.replace(" ", '')) == sorted(mean.replace(" ", '')) or mean in option:
                select_module.logger.debug(f"匹配第{index + 1}个选项选项[{option}]")
                return index
    # 匹配失败 随机提交一个
    select_module.logger.warning("匹配失败，随机提交")
    return random.randint(0, len(options) - 1)


# select match word
def select_match_word(public_info, word_mean) -> int:
    options = filler_option(public_info)
    for word in options:
        # query word mean
        query_word(public_info, word)
        handle_query_word_mean(public_info)
        # is match word mean
        for mean in public_info.word_means:
            if sorted(word_mean.replace(" ", '')) == sorted(mean.replace(" ", '')):
                return public_info.source_option.index(word)
    select_module.logger.error("匹配失败,猜第3个选项")
    return 2


def is_word_exist(public_info, option) -> bool:
    """
    word是否存在word_list中
    :param public_info:
    :param option: word
    :return: None
    """
    if option in public_info.word_list:
        # word is exist word_list
        query_word(public_info, option)
        return True
    else:
        select_module.logger.debug('转原型')
        revert_option = word_revert(option)
        if revert_option in public_info.word_list:
            query_word(public_info, revert_option)
            return True
    return False


# extract sentence word
def word_examples(public_info, options) -> str:
    """
    匹配单词例句中的单词,也就是例句中的单词
    :param public_info:
    :param options: words
    :return: word
    """
    exam_zh = public_info.exam['stem']['remark']
    for word in options:
        if is_word_exist(public_info, word):
            if public_info.word_query_result.get('means'):
                query_result = public_info.word_query_result['means']
                for means in query_result:
                    for examples in means['usages']:
                        for sentences in examples['examples']:
                            # match same mean
                            if sentences["sen_mean_cn"] == exam_zh:
                                # answer
                                return re.findall(r'{(.+?)}', sentences['sen_content'])[0]
            else:
                query_result = public_info.word_query_result['options']
                for contents in query_result:
                    for example in contents['content']['example']:
                        if example["sen_mean_cn"] == exam_zh:
                            # answer
                            return re.findall(r'{(.+?)}', example['sen_content'])[0]
    
    return ''
