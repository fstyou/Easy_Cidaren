import json
import random
import time

from requests.exceptions import RequestException

from easy_cidaren.api import sessions
from easy_cidaren.api.response import (
    UnknownObfuscationError, UnsafeRequestError, WordSelectionRequiredError, handle_task_response as handle_response,
)
from easy_cidaren.app_logging.config import get_logger
from easy_cidaren.security.decode import debase64, JV_TWO, JV_THREE
from easy_cidaren.security.signing import encrypt_md5
from easy_cidaren.utils.helpers import create_timestamp

# create logger
api = get_logger('main_api')

basic_url = 'https://app.vocabgo.com/student/api/Student/'

def request_with_known_jv(request_func, url, *, retry_unknown = False, **kwargs):
    """Retry unreadable encoding versions only for explicitly read-only requests."""
    kwargs.setdefault('timeout', 30)
    attempts = 5 if retry_unknown else 1
    for attempt in range(attempts):
        try:
            response = request_func(url, **kwargs)
            response.raise_for_status( )
        except RequestException as exc:
            if retry_unknown:
                raise
            raise UnsafeRequestError('请求结果不确定，任务已停止；请先在客户端检查任务状态') from exc
        try:
            payload = response.json( )
            jv = str(payload.get('jv') or '')
            if not jv or jv == '0' or jv in JV_TWO or jv in JV_THREE:
                return response
        except (ValueError, AttributeError) as exc:
            if retry_unknown:
                return response
            raise UnsafeRequestError('服务端响应无效，任务已停止；请先在客户端检查任务状态') from exc
        # 普通 Base64 内容无需混淆规则；以解码结果为准，不只检查版本标签。
        try:
            debase64(payload.get('data'), jv)
        except (KeyError, ValueError):
            pass
        else:
            return response
        if attempt + 1 < attempts:
            time.sleep(random.uniform(2, 3))
    api.error("服务端返回未知的 jv 编码版本")
    raise UnknownObfuscationError("服务端返回未知的数据编码版本，请更新程序后重试")


def _handle_changed_response(response):
    try:
        handle_response(response)
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise UnsafeRequestError('服务端已响应，但返回状态无效；请先检查任务状态') from exc


def _update_exam(public_info, response):
    """Interpret the service response once for start, next and skip operations."""
    _handle_changed_response(response)
    try:
        payload = response.json( )
        if payload.get('msg') == '任务已完成！':
            public_info.exam = 'complete'
        elif payload.get('msg') == '需要选词！':
            raise WordSelectionRequiredError('服务端要求先选词，请在客户端完成选词后重试')
        else:
            exam = debase64(payload['data'], payload['jv'])
            if not isinstance(exam, dict) or not exam.get('topic_code'):
                raise ValueError('题目缺少有效的题目编号')
            public_info.exam = exam
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise UnsafeRequestError('服务端已响应，但题目数据无法解析；请先检查任务状态') from exc


def skip_exam(public_info):
    """
    跳过过不了的题目
    :return:
    """
    api.info("无法完成，跳过题目")
    url = 'ClassTask/SkipAnswer'
    params = _answer_parameters(public_info.topic_code, 20000)
    rsp = request_with_known_jv(sessions.answer_session.post, basic_url + url, data = json.dumps(params))
    _update_exam(public_info, rsp)


def _answer_parameters(topic_code, time_spent):
    params = {'it_font_size': 42,
              'it_img_w': 804,
              'opt_font_c': '#000000',
              'opt_font_size': 37,
              'opt_img_w': 684,
              'time_spent': time_spent,
              'timestamp': create_timestamp( ),
              'topic_code': topic_code,
              'version': '2.6.2.24031302'}
    sign = encrypt_md5(
            "&".join([f'{key}={value}' for key, value in params.items( )]) + 'ajfajfamsnfaflfasakljdlalkflak')
    params.update({'sign': sign})
    return params


def select_all_word(word_info, task_id) -> None:
    api.debug("勾选全部单词并提交")
    timestamp = create_timestamp( )
    url = 'ClassTask/SubmitChoseWord'
    # 取消键值对的空格(紧密排版)
    word_map = json.dumps(word_info, separators = (',', ':'))
    source_str = f'chose_err_item=2&task_id={task_id}&timestamp={timestamp}&version=2.6.1.231204&word_map={word_map}ajfajfamsnfaflfasakljdlalkflak'
    sign = encrypt_md5(source_str)
    data = {"task_id": task_id, "word_map": word_info, "chose_err_item": 2,
            "timestamp": timestamp, "version": "2.6.1.231204", "sign": sign,
            "app_type": 1}
    rsp = request_with_known_jv(sessions.selection_session.post, basic_url + url, data = json.dumps(data))
    # 检查请求是否成功
    _handle_changed_response(rsp)


# class task
# 获取所有班级任务
def get_class_task(page_count: int):
    """Return one page of class tasks without mutating UI state."""
    api.info(f'获取第{page_count}页任务')
    url = 'ClassTask/PageTask'
    timestamp = create_timestamp( )
    sign = f"page_count={page_count}&page_size=10&search_type=0&timestamp={timestamp}&version=2.6.1.240122ajfajfamsnfaflfasakljdlalkflak"
    data = {
        'search_type': '0',
        'page_count': page_count,
        'page_size': 10,
        'timestamp': timestamp,
        "version": "2.6.1.231204",
        "sign": encrypt_md5(sign),
        "app_type": 1
    }
    # "task_type": 2 是班级测试任务 1 是班级自学任务
    task = sessions.query_session.post(url = basic_url + url, json = data, timeout = 30)
    # check response is success
    handle_response(task)
    # 转换成字典
    return task.json( )['data']


# start

def get_exam(public_info):
    api.debug("获取第一题")
    url = 'ClassTask/StartAnswer'
    params = {'task_id': public_info.task_id or -1, 'task_type': 2, 'release_id': public_info.release_id,
              'opt_img_w': '684',
              'opt_font_size': '37', 'opt_font_c': '%23000000', 'it_img_w': '804', 'it_font_size': '42',
              'timestamp': create_timestamp( ), 'version': '2.6.1.240122', 'app_type': '1'}
    rsp = request_with_known_jv(sessions.query_session.get, basic_url + url, params = params)
    _update_exam(public_info, rsp)
    api.debug("写入成功")


# next exam
def next_exam(public_info):
    # 获取每一题提交的用时，500为一秒
    min_time = public_info.settings.spend_min_time * 500
    max_time = public_info.settings.spend_max_time * 500
    api.debug("获取下一题")
    url = 'ClassTask/SubmitAnswerAndSave'
    params = _answer_parameters(public_info.topic_code, random.randint(min_time, max_time))
    data = request_with_known_jv(sessions.answer_session.post, basic_url + url, data = json.dumps(params))
    _update_exam(public_info, data)


# 查询单词
def query_word(public_info, word):
    if public_info.is_self_built:
        word_index = public_info.word_list.index(word)
        public_info.now_unit = public_info.get_book_words_data[word_index]['list_id']
    time.sleep(random.randint(0, 2))
    api.debug(f"查询单词{word}")
    url = basic_url + 'Course/StudyWordInfo'
    params = {
        'course_id': public_info.course_id,
        'list_id': public_info.now_unit,
        'word': word,
        'timestamp': create_timestamp( ),
        'version': '2.6.1.231204',
        'app_type': 1
    }
    api.debug(
            f'卡片查询参数: '
            f'course_id={public_info.course_id}, '
            f'list_id={public_info.now_unit}, '
            f'word={word!r}, '
            f'in_word_list={word in public_info.word_list}, '
            f'is_self_built={public_info.is_self_built}'
    )
    response = request_with_known_jv(
            sessions.query_session.get,
            url,
            retry_unknown = True,
            params = params
    )
    handle_response(response)
    public_info.word_query_result = debase64(
            response.json( )['data'],
            response.json( )['jv']
    )
    api.debug("查询单词成功")


# submit word
def submit_result(public_info, option):
    api.debug("开始提交答案")
    timestamp = create_timestamp( )
    topic_code = public_info.topic_code
    sign = encrypt_md5(
            f"answer={option}&timestamp={timestamp}&topic_code={topic_code}&version=2.6.1.231204ajfajfamsnfaflfasakljdlalkflak")
    url = 'ClassTask/VerifyAnswer'
    data = {"answer": option,
            "topic_code": topic_code,
            "timestamp": timestamp, "version": "2.6.1.231204", "sign": sign,
            "app_type": 1}
    rsp = request_with_known_jv(sessions.answer_session.post, basic_url + url, data = json.dumps(data))
    # check request is success
    _handle_changed_response(rsp)
    try:
        payload = rsp.json( )
        result = debase64(payload['data'], payload['jv'])
        if not isinstance(result, dict):
            raise ValueError('答题结果必须是对象')
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise UnsafeRequestError('服务端已响应，但答题结果无法解析；请先检查任务状态') from exc
    answer_result = result.get('answer_result')
    api.debug(f"答题判分: answer_result={answer_result} answer_corrects={result.get('answer_corrects')}")
    return result
