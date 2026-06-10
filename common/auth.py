from functools import wraps

from common.http import error
from common.space import Space


def _resolve_expected_token():
    return Space.auth


def require_login(view_func):
    @wraps(view_func)
    def wrapper(self, request, *args, **kwargs):
        expected = _resolve_expected_token()
        actual = request.headers.get('Authentication', '')
        if not expected or actual != expected:
            return error('UNAUTHORIZED', 'Unauthorized access. Please provide a valid token.', 401)
        return view_func(self, request, *args, **kwargs)

    return wrapper
