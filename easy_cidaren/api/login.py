import json

from requests import exceptions

from easy_cidaren.api import sessions
from easy_cidaren.app_logging.config import get_logger
from easy_cidaren.utils.helpers import create_timestamp

# 基础url
basic_url = 'https://app.vocabgo.com/student/api/'
# 初始化log
login = get_logger("login")


def verify_token(token, *, accept_encoding):
    sessions.set_token(token, accept_encoding = accept_encoding)
    timestamp = create_timestamp( )
    url = f'Student/Main?timestamp={timestamp}&version=2.6.1.231204&app_type=1'
    try:
        response = sessions.query_session.get(basic_url + url, timeout = 15)
        login.info(f"压缩编码格式：{response.headers.get('Content-Encoding')}")
        response.raise_for_status( )  # 检查HTTP状态码
        result = response.json( )
        
        # 登录接口沿用登录失效语义，不套用答题接口的状态码解释。
        if result['code'] != 1:
            login.error("【服务端拒绝登录】: code=%s", result['code'])
            return 1
        return result
    except exceptions.HTTPError as e:
        login.error(f"【HTTP请求错误】: {e}")
        return 2
    except exceptions.Timeout as e:
        login.error(f"【连接超时，请检查网络连接】: {e}")
        return 3
    except json.JSONDecodeError as e:
        login.error(f"【响应内容不是有效的JSON格式】: {e}")
        return 4
    except (KeyError, TypeError) as e:
        login.error('【登录响应格式错误】: %s', e)
        return 4
    except exceptions.SSLError as e:
        login.error(f"【SSL错误】：{e}")
        return 5
    except exceptions.ProxyError as e:
        login.error(f"【代理服务器异常】：{e}")
        return 6
    except exceptions.ConnectionError as e:
        login.error(f"【连接错误】: {e}")
        return 7
