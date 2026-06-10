import json

from django.http import JsonResponse


def ok(body=None, http_code=200, **extra):
    payload = {
        'identifier': 'OK',
        'code': http_code,
        'body': body,
        'http_code': http_code,
    }
    payload.update(extra)
    return JsonResponse(payload, status=http_code, json_dumps_params={'ensure_ascii': False})


def error(identifier: str, msg: str, http_code: int, **extra):
    payload = {
        'identifier': identifier,
        'msg': msg,
        'code': http_code,
        'body': None,
        'http_code': http_code,
    }
    payload.update(extra)
    return JsonResponse(payload, status=http_code, json_dumps_params={'ensure_ascii': False})


def parse_json(request):
    if not request.body:
        return {}
    try:
        return json.loads(request.body.decode('utf-8'))
    except json.JSONDecodeError as exc:
        raise ValueError(f'invalid json body: {exc}') from exc
