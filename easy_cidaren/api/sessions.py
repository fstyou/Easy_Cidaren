import requests

from easy_cidaren.security.signing import encrypt_md5

user_age = 'Mozilla/5.0 (Linux; Android 8.1.2; LIO-AN00 Build/LIO-AN00; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/92.0.4515.131 Safari/537.36 MMWEBID/4462 MicroMessenger/8.0.20.2100(0x28001438) Process/toolsmp WeChat/arm64 Weixin Android Tablet NetType/WIFI Language/zh_CN ABI/arm64'
base_headers = {"Host": "app.vocabgo.com",
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

class _UninitializedSession(requests.Session):
    """Reject requests until login has configured the authenticated sessions."""
    
    def request(self, method, url, params = None, data = None, headers = None,
                cookies = None, files = None, auth = None, timeout = None,
                allow_redirects = True, proxies = None, hooks = None, stream = None,
                verify = None, cert = None, json = None):
        raise RuntimeError('请求会话尚未初始化，请先登录')


query_session: requests.Session = _UninitializedSession( )
answer_session: requests.Session = _UninitializedSession( )
selection_session: requests.Session = _UninitializedSession( )
resource_session: requests.Session = _UninitializedSession( )


def set_token(token: str, *, accept_encoding: str):
    """Replace authenticated connections without reading application state from disk."""
    global query_session, answer_session, selection_session, resource_session
    for session in (query_session, answer_session, selection_session, resource_session):
        session.close( )
    headers = {**base_headers, 'Accept-Encoding': accept_encoding, 'Usertoken': token}
    
    def create_session(overrides):
        result = requests.Session( )
        result.headers.update({**headers, **overrides})
        return result
    
    query_session = create_session({})
    json_headers = {'Origin': 'https://app.vocabgo.com', 'Content-Type': 'application/json'}
    selection_session = create_session(json_headers)
    answer_session = create_session({**json_headers, 'Authorization-V': 'c4ca4238a0b923820dcc509a6f75849b'})
    resource_session = create_session({
        'Origin': 'https://app.vocabgo.com', 'Referer': 'https://app.vocabgo.com',
        'Host': 'resource.vocabgo.com', 'X-Requested-With': 'com.tencent.mm',
    })
    resource_session.headers.pop('Authorization-V')
    resource_session.headers.pop('Abc')
