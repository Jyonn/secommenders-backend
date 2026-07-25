import json
import re


TIMESTAMP_RE = re.compile(r'^\[(?P<hours>\d{2,}):(?P<minutes>\d{2}):(?P<seconds>\d{2})\]')
TRAIN_EPOCH_RE = re.compile(r'\bepoch\s+(?P<epoch>\d+)\s+train_', re.IGNORECASE)
VALID_EPOCH_RE = re.compile(r'\bepoch\s+(?P<epoch>\d+)\s+valid_', re.IGNORECASE)
EARLY_STOP_RE = re.compile(r'\bearly stop at epoch\s+(?P<epoch>\d+)\b', re.IGNORECASE)
FINAL_BEST_RE = re.compile(r'\bbest_epoch=(?P<epoch>\d+)\b', re.IGNORECASE)


def _timestamp_seconds(line: str):
    match = TIMESTAMP_RE.search(line)
    if not match:
        return None
    return (
        int(match.group('hours')) * 3600
        + int(match.group('minutes')) * 60
        + int(match.group('seconds'))
    )


def _average(values: list[float]):
    if not values:
        return None
    return sum(values) / len(values)


def parse_epoch_summary(log: str | None):
    if not log:
        return None

    start_seconds = None
    train_marks = {}
    valid_marks = {}
    epoch_numbers = set()
    best_epoch = None
    early_stop_epoch = None

    for raw_line in str(log).splitlines():
        line = raw_line.strip()
        seconds = _timestamp_seconds(line)
        if seconds is not None and start_seconds is None and 'start training' in line.lower():
            start_seconds = seconds

        train_match = TRAIN_EPOCH_RE.search(line)
        if train_match:
            epoch = int(train_match.group('epoch'))
            epoch_numbers.add(epoch)
            if seconds is not None:
                train_marks.setdefault(epoch, seconds)

        valid_match = VALID_EPOCH_RE.search(line)
        if valid_match:
            epoch = int(valid_match.group('epoch'))
            epoch_numbers.add(epoch)
            if seconds is not None:
                valid_marks.setdefault(epoch, seconds)

        early_stop_match = EARLY_STOP_RE.search(line)
        if early_stop_match:
            early_stop_epoch = int(early_stop_match.group('epoch'))
            epoch_numbers.add(early_stop_epoch)

        best_match = FINAL_BEST_RE.search(line)
        if best_match:
            best_epoch = int(best_match.group('epoch'))
            epoch_numbers.add(best_epoch)

    if not epoch_numbers:
        return None

    train_durations = []
    eval_durations = []
    for epoch in sorted(epoch_numbers):
        train_seconds = train_marks.get(epoch)
        valid_seconds = valid_marks.get(epoch)
        previous_valid_seconds = valid_marks.get(epoch - 1)
        if epoch == 1 and previous_valid_seconds is None:
            previous_valid_seconds = start_seconds
        if train_seconds is not None and previous_valid_seconds is not None and train_seconds >= previous_valid_seconds:
            train_durations.append(float(train_seconds - previous_valid_seconds))
        if train_seconds is not None and valid_seconds is not None and valid_seconds >= train_seconds:
            eval_durations.append(float(valid_seconds - train_seconds))

    summary = {
        'trained_epochs': max(epoch_numbers),
        'log_best_epoch': best_epoch,
        'early_stop_epoch': early_stop_epoch,
        'avg_train_epoch_seconds': _average(train_durations),
        'avg_eval_epoch_seconds': _average(eval_durations),
        'train_epoch_count': len(train_marks),
        'eval_epoch_count': len(valid_marks),
        'parsed_epoch_count': len(epoch_numbers),
        'parser': 'timestamp-keyword.v1',
    }
    return summary


def dumps_epoch_summary(summary: dict | None):
    if not summary:
        return ''
    return json.dumps(summary, ensure_ascii=False, sort_keys=True)
