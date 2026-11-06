import json
import re

from easy_cidaren.api import sessions
from easy_cidaren.api.response import handle_response
from easy_cidaren.app_logging.config import get_logger
from easy_cidaren.utils.helpers import create_timestamp

basic_api = get_logger("basic_api")
basic_url = 'https://app.vocabgo.com/student/api/Student/'


def use_api_get_prototype(word: str) -> str | None:
    """
    利用api获取单词原型
    :param word: 目标单词
    :return: 原型
    """
    basic_api.info(f"单词{word}走api转原型")
    params = {'word': word, 'timestamp': create_timestamp( ),
              'version': '2.6.2.24031302', 'app_type': 1}
    prototype = sessions.query_session.get(basic_url + 'Course/SearchWord', params = params, timeout = 30)
    prototype.encoding = 'utf-8'  # 设置编码
    handle_response(prototype)
    
    # 提取并解码数据
    meaning_str: str = prototype.json( )['data']['word_mean']['meaning']

    # 只解码残留的 Unicode 转义，保留已经解码的非 ASCII 文本。
    def decode_escape(match: re.Match[str]) -> str:
        return json.loads('"' + match.group( ) + '"')

    decoded_meaning = re.sub(r'(?:\\u[0-9a-fA-F]{4})+', decode_escape, meaning_str)
    # 正则匹配
    result = re.findall(r'<span>(.+?)</span>', decoded_meaning)
    return None if not result else result[0]


def get_all_unit(public_info):
    """
    获取课程所有单元
    """
    timestamp = create_timestamp( )
    url = f'StudyTask/List?course_id={public_info.course_id}&timestamp={timestamp}&version=2.6.1.231204&app_type=1'
    user_data = sessions.query_session.get(basic_url + url, timeout = 30)
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
    word_data = sessions.query_session.get(basic_url + 'StudyTask/Info', params = url_params, timeout = 30)
    # 检查请求是否成功
    handle_response(word_data)
    word_data_json = word_data.json( )
    basic_api.debug("单词数据：%s", word_data_json, extra = {'file_only': True})
    public_info.get_word_list_result = word_data_json


def get_book_all_words(public_info):
    basic_api.info('获取该本书的所有单词')
    url = f'https://resource.vocabgo.com/Resource/CoursePage/{public_info.course_id}.json'
    rsp = sessions.resource_session.get(url, timeout = 30)
    rsp.raise_for_status( )
    # all the words in the book
    public_info.get_book_words_data = rsp.json( )
