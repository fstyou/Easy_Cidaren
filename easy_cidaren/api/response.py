"""Validate service responses and report protocol errors."""

from easy_cidaren.app_logging.config import get_logger

logger = get_logger('api_response')


class CardDataError(Exception):
    """The current word card is invalid."""


class SecurityVerifyError(Exception):
    """The service requires the user to complete security verification."""


class UnsafeRequestError(Exception):
    """The result of a state-changing request is uncertain and must not be repeated."""


class UnknownObfuscationError(UnsafeRequestError):
    """The response uses an unknown obfuscation version."""


def handle_response(response, *, task = False):
    response.raise_for_status( )
    data = response.json( )
    code = data['code']
    logger.debug('接口响应：%s', response.text, extra = {'file_only': True})
    if code == 1 or (task and ((code == 20001 and data.get('data')) or code == 20004)):
        return
    if code == 11003:
        logger.error('服务端要求安全验证（code=11003）')
        raise SecurityVerifyError('服务端需安全验证，请打开词达人 App/微信完成安全验证后重试')
    if task and code == 120:
        logger.error('卡片数据异常（code=120）')
        raise CardDataError('当前单词卡片数据异常')
    if task and code == 0 and data.get('msg') == '加载单词卡片失败，请重新加载':
        raise RuntimeError('查找不到单词，请手动答题')
    logger.error('服务端请求失败（code=%s，消息=%s）', code, data.get('msg', '未知错误'))
    raise RuntimeError('服务端请求失败')


def handle_task_response(response):
    handle_response(response, task = True)
