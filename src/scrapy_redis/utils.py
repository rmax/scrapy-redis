import json
from json import JSONDecodeError

import six


class TextColor:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


def bytes_to_str(s, encoding="utf-8"):
    """Returns a str if a bytes object is given."""
    if six.PY3 and isinstance(s, bytes):
        return s.decode(encoding)
    return s


def is_dict(string_content):
    """Try load string_content as json, if failed, return False, else return True."""
    try:
        json.loads(string_content)
    except JSONDecodeError:
        return False
    return True


def convert_bytes_to_str(data, encoding="utf-8"):
    """Convert a dict's keys & values from `bytes` to `str`
    or convert bytes to str"""
    if isinstance(data, bytes):
        return data.decode(encoding)
    if isinstance(data, dict):
        return dict(map(convert_bytes_to_str, data.items()))
    elif isinstance(data, tuple):
        return map(convert_bytes_to_str, data)
    return data
