import hashlib


def encrypt_md5(data: str) -> str:
    """
    MD5加密
    :param data:
    :return:
    """
    md5 = hashlib.md5( )
    md5.update(data.encode( ))
    return md5.hexdigest( )
