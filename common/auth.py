from functools import wraps

from django.db import OperationalError, ProgrammingError

from common.http import error
from common.space import Space


def _resolve_expected_token():
    try:
        from config.models import ConfigEntry

        value = ConfigEntry.get('auth', default=None)
        if value:
            return value
    except (OperationalError, ProgrammingError):
        pass
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
