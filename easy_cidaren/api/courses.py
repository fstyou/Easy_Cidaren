import re

import easy_cidaren.api.sessions as requests
from easy_cidaren.api.response import handle_response
from easy_cidaren.logging.config import Log
from easy_cidaren.utils.helpers import create_timestamp

basic_api = Log("basic_api")
basic_url = 'https://app.vocabgo.com/student/api/Student/'


def use_api_get_prototype(word: str) -> str:
    """
    利用api获取单词原型
    :param word: 目标单词
    :return: 原型
    """
    basic_api.logger.info(f"单词{word}走api转原型")
    params = {'word': word, 'timestamp': create_timestamp( ),
              'version': '2.6.2.24031302', 'app_type': 1}
    prototype = requests.rqs_session.get(basic_url + 'Course/SearchWord', params = params, timeout = 30)
    prototype.encoding = 'utf-8'  # 设置编码
    handle_response(prototype)
    
    # 提取并解码数据
    meaning_str = prototype.json( )['data']['word_mean']['meaning']
    # 处理转义字符
    decoded_meaning = bytes(meaning_str, 'utf-8').decode('unicode_escape')
    # 正则匹配
    result = re.findall(r'<span>(.+?)</span>', decoded_meaning)
    return None if not result else result[0]


def get_all_unit(public_info):
    """
    获取课程所有单元
    """
    timestamp = create_timestamp( )
    url = f'StudyTask/List?course_id={public_info.course_id}&timestamp={timestamp}&version=2.6.1.231204&app_type=1'
    user_data = requests.rqs_session.get(basic_url + url, timeout = 30)
    # 检查请求是否成功
    handle_response(user_data)
    public_info.all_unit = user_data.json( )['data']


# 获取单元所有单词
def get_unit_words(public_info):
    timestamp = create_timestamp( )
    url_params = {'task_id': public_info.task_id or -1, "course_id": public_info.course_id, 'timestamp': timestamp,
                  'version': '2.6.1.240305', 'app_type': '1'}
    if public_info.is_self_built:
        # 自建任务
        url_params.update({'release_id': public_info.release_id})
    else:
        # 测试任务
        url_params.update({'list_id': public_info.now_unit})
    word_data = requests.rqs_session.get(basic_url + 'StudyTask/Info', params = url_params, timeout = 30)
    # 检查请求是否成功
    handle_response(word_data)
    word_data_json = word_data.json( )
    basic_api.logger.debug("单词数据：%s", word_data_json, extra = {'file_only': True})
    public_info.get_word_list_result = word_data_json


def get_book_all_words(public_info):
    basic_api.logger.info('获取该本书的所有单词')
    url = f'https://resource.vocabgo.com/Resource/CoursePage/{public_info.course_id}.json'
    rsp = requests.rsq_self_built.get(url, timeout = 30)
    # all the words in the book
    public_info.get_book_words_data = rsp.json( )
