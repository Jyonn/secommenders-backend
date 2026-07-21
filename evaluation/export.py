from django.utils.dateparse import parse_datetime

from evaluation.models import Evaluation, Experiment


def normalize_filter_values(value, *, lowercase=True):
    if not value:
        return []
    if isinstance(value, (list, tuple)):
        raw_values = value
    else:
        raw_values = [value]
    values = []
    for item in raw_values:
        values.extend(str(part).strip() for part in str(item).split(',') if str(part).strip())
    if lowercase:
        return [item.lower() for item in values]
    return values


def get_total_running_hours():
    running_seconds = 0.0
    for experiment in Experiment.objects.all():
        if experiment.runtime_seconds is not None:
            running_seconds += float(experiment.runtime_seconds)
        elif experiment.started_at and experiment.completed_at:
            running_seconds += (experiment.completed_at - experiment.started_at).total_seconds()
        else:
            meta = experiment.dictify_meta() or {}
            meta_runtime = meta.get('runtime_seconds')
            if meta_runtime is not None:
                try:
                    running_seconds += float(meta_runtime)
                    continue
                except (TypeError, ValueError):
                    pass
            started_at = parse_datetime(str(meta.get('started_at') or ''))
            ended_at = parse_datetime(
                str(meta.get('finished_at') or meta.get('completed_at') or meta.get('failed_at') or '')
            )
            if started_at and ended_at and ended_at > started_at:
                running_seconds += (ended_at - started_at).total_seconds()
    return running_seconds / 3600.0


def get_leaderboard(
    *,
    replicate=1,
    metric='ndcg@10',
    data_name=None,
    model_name=None,
    task_type=None,
    repr_type=None,
    limit=50,
):
    metric = str(metric).lower()
    evaluations = Evaluation.objects.all().order_by('-modified_at')
    for field_name, value in [
        ('data_name', data_name),
        ('model_name', model_name),
        ('task_type', task_type),
        ('repr_type', repr_type),
    ]:
        values = normalize_filter_values(value)
        if values:
            evaluations = evaluations.filter(**{f'{field_name}__in': values})

    rows = []
    for evaluation in evaluations:
        completed = evaluation.experiment_set.filter(is_completed=True).count()
        if completed < int(replicate):
            continue
        performance = evaluation.prettify_performance(metrics=[metric])
        stats = performance.get(metric)
        if not stats:
            continue
        rows.append(
            {
                'signature': evaluation.signature,
                'name': evaluation.name,
                'plan_name': evaluation.plan_name,
                'data_name': evaluation.data_name,
                'model_name': evaluation.model_name,
                'task_type': evaluation.task_type,
                'repr_type': evaluation.repr_type,
                'run_id': evaluation.run_id,
                'metric': metric,
                'mean': stats[0],
                'std': stats[1],
                'replicate': completed,
                'performance': evaluation.prettify_performance(),
            }
        )
    rows.sort(key=lambda row: row['mean'], reverse=True)
    return rows[: int(limit)]
