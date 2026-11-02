import time


def create_timestamp( ) -> int:
    return int(time.time( ) * 1000)


def delete_other_char(result: str) -> str:
    delete_list = ['}', '{', ' ...', ' …']
    for delete_str in delete_list:
        result = result.replace(delete_str, '')
    return result.replace(' ', ',')
