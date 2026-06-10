import json


def json_loads(value, default=None):
    if value in (None, ''):
        return default
    if isinstance(value, (dict, list)):
        return value
    return json.loads(value)


def json_dumps(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True)
