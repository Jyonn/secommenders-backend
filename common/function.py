def parse_int(value, default=None, minimum=None, maximum=None):
    if value in (None, ''):
        return default
    value = int(value)
    if minimum is not None:
        value = max(value, minimum)
    if maximum is not None:
        value = min(value, maximum)
    return value


def parse_csv(value):
    if value in (None, ''):
        return None
    return [part.strip() for part in str(value).split(',') if part.strip()]


def compact_text(value, limit=500):
    if value is None:
        return None
    value = str(value).strip()
    if len(value) <= limit:
        return value
    return value[: limit - 3] + '...'
