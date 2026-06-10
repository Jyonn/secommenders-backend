from collections import defaultdict
import math

from evaluation.models import Evaluation


def _safe_mean_std(values):
    if not values:
        return None
    mean = sum(values) / len(values)
    if len(values) <= 1:
        return mean, 0.0
    variance = sum((value - mean) ** 2 for value in values) / (len(values) - 1)
    return mean, math.sqrt(variance)


def get_total_running_hours():
    running_seconds = 0.0
    for evaluation in Evaluation.objects.all():
        for experiment in evaluation.experiment_set.filter(is_completed=True):
            if experiment.runtime_seconds is not None:
                running_seconds += float(experiment.runtime_seconds)
    return running_seconds / 3600.0


def get_top_rank_models_per_datasets(replicate=1, metrics=None, datasets=None, top_k=1):
    metrics = [metric.lower() for metric in (metrics or ['ndcg@10'])]
    dataset_whitelist = {dataset.lower() for dataset in datasets} if datasets else None

    grouped = defaultdict(list)
    for evaluation in Evaluation.objects.all():
        completed = evaluation.experiment_set.filter(is_completed=True)
        if completed.count() < int(replicate):
            continue
        configuration = evaluation.prettify_configuration() or {}
        dataset = str(configuration.get('data') or '').lower()
        if dataset_whitelist and dataset not in dataset_whitelist:
            continue
        if not dataset:
            continue
        score = evaluation.export_rank_performance(metrics)
        grouped[dataset].append((evaluation, score))

    results = {}
    for dataset, entries in grouped.items():
        entries.sort(key=lambda item: item[1], reverse=True)
        ranked = []
        for evaluation, _ in entries[:top_k]:
            ranked.append(
                {
                    'signature': evaluation.signature,
                    'name': evaluation.name,
                    'command': evaluation.command,
                    'performance': evaluation.prettify_performance(metrics=metrics),
                }
            )
        results[dataset] = ranked
    return results
