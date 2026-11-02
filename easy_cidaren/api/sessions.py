import requests

from easy_cidaren.core.public_info import PublicInfo
from easy_cidaren.security.signing import encrypt_md5

user_age = 'Mozilla/5.0 (Linux; Android 8.1.2; LIO-AN00 Build/LIO-AN00; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/92.0.4515.131 Safari/537.36 MMWEBID/4462 MicroMessenger/8.0.20.2100(0x28001438) Process/toolsmp WeChat/arm64 Weixin Android Tablet NetType/WIFI Language/zh_CN ABI/arm64'
headers = {"Host": "app.vocabgo.com",
           "Accept": "application/json, text/plain, */*",
           "Abc": encrypt_md5(user_age),
           "Authorization-V": "cfcd208495d565ef66e7dff9f98764da",
           "X-Requested-With": "XMLHttpRequest",
           "User-Agent": user_age,
           "Accept-Language": "*",
           "Sec-Fetch-Site": "same-origin",
           "Sec-Fetch-Mode": "cors",
           "Sec-Fetch-Dest": "empty",
           "Referer": "https://app.vocabgo.com/student/"
           }

rqs_session = rqs2_session = rqs3_session = class_task_request = rsq_self_built = ''


def set_token(token):
    global rqs_session, rqs2_session, rqs3_session, class_task_request, rsq_self_built
    requests.DEFAULT_RETRIES = 5
    session_headers = {**headers, 'Accept-Encoding': PublicInfo( ).accept_encoding, 'Usertoken': token}
    rqs_session = requests.session( )
    rqs_session.headers = session_headers.copy( )
    # submit request header
    rqs2_session = requests.session( )
    rqs2_session.keep_alive = False
    rqs2_session.headers = session_headers.copy( )
    rqs2_session.headers.update(
            {"Authorization-V": "c4ca4238a0b923820dcc509a6f75849b", 'Usertoken': token,
             "Origin": "https://app.vocabgo.com",
             "Content-Type": "application/json"})
    rqs3_session = requests.session( )
    rqs3_session.headers = session_headers.copy( )
    rqs3_session.headers.update({"Origin": "https://app.vocabgo.com", 'Usertoken': token,
                                 "Content-Type": "application/json"})
    class_task_request = requests.session( )
    class_task_request.headers = rqs_session.headers.copy( )
    # self_built request
    rsq_self_built = requests.session( )
    rsq_self_built.headers = session_headers.copy( )
    rsq_self_built.headers.update(
            {"Origin": "https://app.vocabgo.com", "Referer": "https://app.vocabgo.com", "Host": 'resource.vocabgo.com',
             "X-Requested-With": 'com.tencent.mm'})
    rsq_self_built.headers.pop('Authorization-V')
    rsq_self_built.headers.pop('Abc')
