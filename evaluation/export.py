from evaluation.models import Evaluation

def get_total_running_hours():
    running_seconds = 0.0
    for evaluation in Evaluation.objects.all():
        for experiment in evaluation.experiment_set.filter(is_completed=True):
            if experiment.runtime_seconds is not None:
                running_seconds += float(experiment.runtime_seconds)
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
    if data_name:
        evaluations = evaluations.filter(data_name=str(data_name).lower())
    if model_name:
        evaluations = evaluations.filter(model_name=str(model_name).lower())
    if task_type:
        evaluations = evaluations.filter(task_type=str(task_type).lower())
    if repr_type:
        evaluations = evaluations.filter(repr_type=str(repr_type).lower())

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
