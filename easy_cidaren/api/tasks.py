import json
import random
import time
from functools import wraps

import easy_cidaren.api.sessions as requests
from easy_cidaren.api.response import handle_task_response as handle_response
from easy_cidaren.core.public_info import PublicInfo
from easy_cidaren.logging.config import Log
from easy_cidaren.security.decode import debase64, JV_TWO, JV_THREE
from easy_cidaren.security.signing import encrypt_md5
from easy_cidaren.utils.helpers import create_timestamp

# create logger
api = Log('main_api')

basic_url = 'https://app.vocabgo.com/student/api/Student/'

def request_with_known_jv(request_func, url, **kwargs):
    """Retry responses with an unknown obfuscation version."""
    kwargs.setdefault('timeout', 30)
    for _ in range(5):
        response = request_func(url, **kwargs)
        try:
            jv = str(response.json( ).get('jv', ''))
            if not jv or jv == '0' or jv in JV_TWO or jv in JV_THREE:
                return response
        except Exception:
            return response
        time.sleep(random.uniform(2, 3))
    api.logger.error("连续 5 次请求的 jv 均不在已知范围内")
    raise ValueError("jv 解码失败")


def skip_exam(public_info):
    """
    跳过过不了的题目
    :return:
    """
    api.logger.info("无法完成，跳过题目")
    url = f'{PublicInfo.task_type}/SkipAnswer'
    params = {'it_font_size': 42,
              'it_img_w': 804,
              'opt_font_c': '#000000',
              'opt_font_size': 37,
              'opt_img_w': 684,
              'time_spent': 20000,
              'timestamp': create_timestamp( ),
              'topic_code': public_info.topic_code,
              'version': '2.6.2.24031302'}
    sign = encrypt_md5(
            "&".join([f'{key}={value}' for key, value in params.items( )]) + 'ajfajfamsnfaflfasakljdlalkflak')
    params.update({'sign': sign})
    rsp = request_with_known_jv(requests.rqs2_session.post, basic_url + url, data = json.dumps(params))
    # check response is success
    handle_response(rsp)
    # 检查jv
    # update exam
    if rsp.json( )['msg'] == '任务已完成！' or rsp.json( )['msg'] == '需要选词！':
        public_info.exam = 'complete'
    # decrypt response
    else:
        public_info.exam = debase64(rsp.json( )['data'], rsp.json( )['jv'])


# 勾选所有单词 bug
def select_all_word(word_info, task_id: int, ) -> None:
    api.logger.debug("勾选全部单词并提交")
    timestamp = create_timestamp( )
    url = f'{PublicInfo.task_type}/SubmitChoseWord'
    # 取消键值对的空格(紧密排版)
    word_map = json.dumps(word_info, separators = (',', ':'))
    source_str = f'chose_err_item=2&task_id={task_id}&timestamp={timestamp}&version=2.6.1.231204&word_map={word_map}ajfajfamsnfaflfasakljdlalkflak'
    sign = encrypt_md5(source_str)
    data = {"task_id": task_id, "word_map": word_info, "chose_err_item": 2,
            "timestamp": timestamp, "version": "2.6.1.231204", "sign": sign,
            "app_type": 1}
    rsp = request_with_known_jv(requests.rqs3_session.post, basic_url + url, data = json.dumps(data))
    # 检查请求是否成功
    handle_response(rsp)


# class task
# 获取所有班级任务
def get_class_task(public_info, page_count: int):
    """
    :param public_info:
    :param page_count:  第几页的数据
    :return:
    """
    api.logger.info(f'获取第{page_count}页任务')
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
    task = requests.class_task_request.post(url = basic_url + url, json = data, timeout = 30)
    # check response is success
    handle_response(task)
    # 转换成字典
    task_dict = task.json( )
    public_info.class_task.append(task_dict['data'])
    # number of task
    public_info.task_total_count = task_dict['data']['total']


# start

def get_exam(public_info):
    api.logger.debug("获取第一题")
    url = f'{PublicInfo.task_type}/StartAnswer'
    params = {'task_id': public_info.task_id or -1, 'task_type': PublicInfo.task_type_int,
              'opt_img_w': '684',
              'opt_font_size': '37', 'opt_font_c': '%23000000', 'it_img_w': '804', 'it_font_size': '42',
              'timestamp': create_timestamp( ), 'version': '2.6.1.240122', 'app_type': '1'}
    if PublicInfo.task_type_int == 2:
        params.update({'release_id': public_info.release_id})
    else:
        params.update({'course_id': public_info.course_id})
    rsp = request_with_known_jv(requests.class_task_request.get, basic_url + url, params = params)
    # {'task_id': 143960071, 'task_type': 1, 'topic_mode': 0, 'stem': {'content': 'trade', 'remark': None, 'ph_us_url': '/Resource/unitAudio_US/JJ_3_1_0/trade.mp3', 'ph_en_url': '/Resource/unitAudio_EN/JJ_3_1_0/trade.mp3', 'au_addr': None}, 'options': [{'content': 'verb 互相交换', 'remark': None, 'answer': None, 'answer_tag': 0, 'check_code': None, 'sub_options': None, 'ph_info': {'ph_en': 'treɪd', 'ph_en_url': '/Resource/unitAudio_EN/JJ_3_1_0/trade.mp3', 'ph_us': 'treɪd', 'ph_us_url': '/Resource/unitAudio_US/JJ_3_1_0/trade.mp3', 'group': '0'}}, {'content': 'noun 职业；手艺', 'remark': None, 'answer': None, 'answer_tag': 1, 'check_code': None, 'sub_options': None, 'ph_info': {'ph_en': 'treɪd', 'ph_en_url': '/Resource/unitAudio_EN/JJ_3_1_0/trade.mp3', 'ph_us': 'treɪd', 'ph_us_url': '/Resource/unitAudio_US/JJ_3_1_0/trade.mp3', 'group': '0'}}], 'sound_mark': 'treɪd', 'ph_en': 'treɪd', 'ph_us': 'treɪd', 'answer_num': 1, 'chance_num': 1, 'topic_done_num': 1, 'topic_total': 127, 'w_lens': [], 'w_len': 0, 'w_tip': '', 'tips': '', 'word_type': 1, 'enable_i': 2, 'enable_i_i': 2, 'enable_i_o': 2, 'topic_code': 'lFiAe5drW46DfnrEaJVol2hbXlrWqpianVhlZmGZlmKPvo+UkWOTZWdiYm9ubJuXamCVaGpnaGSUj2STZGhob2JybGuWnG5tjZRlZWuVcmxmYW9pZZSSZ2mebmZtcWRsZWiZaWdsZGaW', 'answer_state': 1, 'show_card_type': 1}
    # 检查请求结果
    handle_response(rsp)
    if rsp.json( ).get('msg') == '任务已完成！' or rsp.json( ).get('msg') == '需要选词！':
        public_info.exam = 'complete'
        return
    #  decrypt response
    public_info.exam = debase64(rsp.json( )['data'], rsp.json( )['jv'])
    api.logger.debug("写入成功")


# next exam
def next_exam(public_info):
    # 获取每一题提交的用时，500为一秒
    min_time = public_info.spend_min_time * 500
    max_time = public_info.spend_max_time * 500
    api.logger.debug("获取下一题")
    url = f'{PublicInfo.task_type}/SubmitAnswerAndSave'
    params = {'it_font_size': 42,
              'it_img_w': 804,
              'opt_font_c': '#000000',
              'opt_font_size': 37,
              'opt_img_w': 684,
              'time_spent': random.randint(min_time, max_time),
              'timestamp': create_timestamp( ),
              'topic_code': public_info.topic_code,
              'version': '2.6.2.24031302'}
    sign = encrypt_md5(
            "&".join([f'{key}={value}' for key, value in params.items( )]) + 'ajfajfamsnfaflfasakljdlalkflak')  # 加密
    params.update({'sign': sign})
    data = request_with_known_jv(requests.rqs2_session.post, basic_url + url, data = json.dumps(params))
    # 检查请求是否成功
    handle_response(data)
    if data.json( )['msg'] == '任务已完成！' or data.json( )['msg'] == '需要选词！':
        public_info.exam = 'complete'
    # decrypt response
    else:
        public_info.exam = debase64(data.json( )['data'], data.json( )['jv'])


def check_is_self_built(func):
    @wraps(func)
    def is_self_built(public_info, word):
        if public_info.is_self_built:
            # 从单词列表获取索引
            word_index = public_info.word_list.index(word)
            # 获取单元单词
            public_info.now_unit = public_info.get_book_words_data[word_index]["list_id"]
        return func(public_info, word)
    
    return is_self_built


# 查询单词
@check_is_self_built
def query_word(public_info, word):
    time.sleep(random.randint(0, 2))
    api.logger.debug(f"查询单词{word}")
    url = basic_url + 'Course/StudyWordInfo'
    params = {
        'course_id': public_info.course_id,
        'list_id': public_info.now_unit,
        'word': word,
        'timestamp': create_timestamp( ),
        'version': '2.6.1.231204',
        'app_type': 1
    }
    api.logger.debug(
            f'卡片查询参数: '
            f'course_id={public_info.course_id}, '
            f'list_id={public_info.now_unit}, '
            f'word={word!r}, '
            f'in_word_list={word in public_info.word_list}, '
            f'is_self_built={public_info.is_self_built}'
    )
    response = request_with_known_jv(
            requests.rqs_session.get,
            url,
            params = params
    )
    handle_response(response)
    public_info.word_query_result = debase64(
            response.json( )['data'],
            response.json( )['jv']
    )
    api.logger.debug("查询单词成功")


# submit word
def submit_result(public_info, option):
    api.logger.debug("开始提交答案")
    timestamp = create_timestamp( )
    topic_code = public_info.topic_code
    sign = encrypt_md5(
            f"answer={option}&timestamp={timestamp}&topic_code={topic_code}&version=2.6.1.231204ajfajfamsnfaflfasakljdlalkflak")
    url = f"{PublicInfo.task_type}/VerifyAnswer"
    data = {"answer": option,
            "topic_code": topic_code,
            "timestamp": timestamp, "version": "2.6.1.231204", "sign": sign,
            "app_type": 1}
    rsp = request_with_known_jv(requests.rqs2_session.post, basic_url + url, data = json.dumps(data))
    # check request is success
    handle_response(rsp)
    result = debase64(rsp.json( )['data'], rsp.json( )['jv'])
    answer_result = result.get('answer_result')
    api.logger.debug(f"答题判分: answer_result={answer_result} answer_corrects={result.get('answer_corrects')}")
    return result
