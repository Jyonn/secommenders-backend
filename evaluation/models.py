import json
from datetime import timedelta

from django.db import models
from django.utils import timezone
from django.utils.crypto import get_random_string


class Evaluation(models.Model):
    signature = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=200, blank=True)
    command = models.TextField(unique=True)
    configuration = models.TextField()
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    @classmethod
    def create(cls, signature, command, configuration, name=''):
        return cls.objects.create(
            signature=signature,
            command=command,
            configuration=configuration,
            name=name or '',
        )

    @classmethod
    def create_or_get(cls, signature, command, configuration, name=''):
        evaluation, created = cls.objects.get_or_create(
            command=command,
            defaults={
                'signature': signature,
                'configuration': configuration,
                'name': name or '',
            },
        )
        dirty = False
        if evaluation.signature != signature:
            evaluation.signature = signature
            dirty = True
        if evaluation.configuration != configuration:
            evaluation.configuration = configuration
            dirty = True
        if name and evaluation.name != name:
            evaluation.name = name
            dirty = True
        if dirty:
            evaluation.save()
        return evaluation

    @classmethod
    def get_by_signature(cls, signature):
        return cls.objects.get(signature=signature)

    def prettify_configuration(self):
        if not self.configuration:
            return None
        return json.loads(self.configuration)

    def prettify_performance(self, metrics=None):
        metrics = {metric.lower() for metric in metrics} if metrics else None
        buckets = {}
        for experiment in self.experiment_set.filter(is_completed=True):
            performance = experiment.dictify_performance() or {}
            for metric, value in performance.items():
                metric_key = str(metric).lower()
                if metrics and metric_key not in metrics:
                    continue
                buckets.setdefault(metric_key, []).append(float(value))
        summary = {}
        for metric, values in buckets.items():
            mean = sum(values) / len(values)
            if len(values) <= 1:
                std = 0.0
            else:
                variance = sum((value - mean) ** 2 for value in values) / (len(values) - 1)
                std = variance ** 0.5
            summary[metric] = [mean, std]
        return summary

    def export_rank_performance(self, metrics):
        values = []
        wanted = [metric.lower() for metric in metrics]
        for experiment in self.experiment_set.filter(is_completed=True):
            performance = {str(key).lower(): value for key, value in (experiment.dictify_performance() or {}).items()}
            for metric in wanted:
                if metric not in performance:
                    return 0.0
                values.append(float(performance[metric]))
        if not values:
            return 0.0
        return sum(values) / len(values)

    def jsonl(self):
        return {
            'signature': self.signature,
            'name': self.name,
            'command': self.command,
            'created_at': self.created_at.astimezone().isoformat(),
            'modified_at': self.modified_at.astimezone().isoformat(),
            'comment': self.comment,
            'experiments': [experiment.jsonl() for experiment in self.experiment_set.all().order_by('seed', 'created_at')],
        }

    def json(self):
        return {
            'signature': self.signature,
            'name': self.name,
            'command': self.command,
            'configuration': self.prettify_configuration(),
            'created_at': self.created_at.astimezone().isoformat(),
            'modified_at': self.modified_at.astimezone().isoformat(),
            'comment': self.comment,
            'experiments': [experiment.json() for experiment in self.experiment_set.all().order_by('seed', 'created_at')],
        }

    def __str__(self):
        return self.name or self.signature


class Experiment(models.Model):
    STATUS_CREATED = 'created'
    STATUS_RUNNING = 'running'
    STATUS_COMPLETED = 'completed'
    STATUS_FAILED = 'failed'
    STATUS_CHOICES = [
        (STATUS_CREATED, 'created'),
        (STATUS_RUNNING, 'running'),
        (STATUS_COMPLETED, 'completed'),
        (STATUS_FAILED, 'failed'),
    ]

    evaluation = models.ForeignKey(Evaluation, on_delete=models.CASCADE)
    seed = models.IntegerField(default=42)
    session = models.CharField(max_length=32, unique=True)
    phase = models.CharField(max_length=32, blank=True)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default=STATUS_CREATED)
    pid = models.IntegerField(null=True, blank=True)
    hostname = models.CharField(max_length=255, blank=True)
    run_dir = models.TextField(blank=True)
    log_path = models.TextField(blank=True)
    command = models.TextField(blank=True)
    log = models.TextField(blank=True)
    meta = models.TextField(blank=True)
    performance = models.TextField(blank=True)
    error = models.TextField(blank=True)
    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    runtime_seconds = models.FloatField(null=True, blank=True)

    @classmethod
    def create(cls, evaluation, seed):
        return cls.objects.create(
            evaluation=evaluation,
            seed=seed,
            session=get_random_string(length=32),
        )

    @classmethod
    def create_or_get(cls, evaluation, seed):
        try:
            return cls.objects.get(evaluation=evaluation, seed=seed)
        except cls.DoesNotExist:
            return cls.create(evaluation, seed)

    @classmethod
    def get_by_session(cls, session):
        return cls.objects.get(session=session)

    @classmethod
    def get(cls, signature=None, seed=None, session=None):
        if session:
            return cls.get_by_session(session)
        if signature is None or seed is None:
            raise cls.DoesNotExist('query requires session or (signature, seed)')
        evaluation = Evaluation.get_by_signature(signature)
        return cls.create_or_get(evaluation, seed)

    def register(self, pid=None, hostname='', run_dir='', log_path='', command='', phase=''):
        self.pid = pid
        self.hostname = hostname or self.hostname
        self.run_dir = run_dir or self.run_dir
        self.log_path = log_path or self.log_path
        self.command = command or self.command
        self.phase = phase or self.phase
        self.status = self.STATUS_RUNNING
        self.started_at = timezone.now()
        self.completed_at = None
        self.runtime_seconds = None
        self.error = ''
        self.is_completed = False
        self.save()

    def update_state(self, *, status=None, phase=None, log=None, meta=None, performance=None, error=None):
        if status:
            self.status = status
        if phase:
            self.phase = phase
        if log is not None:
            self.log = log
        if meta is not None:
            self.meta = meta
        if performance is not None:
            self.performance = performance
        if error is not None:
            self.error = error
        if self.status == self.STATUS_COMPLETED:
            self.is_completed = True
            self.completed_at = timezone.now()
        elif self.status == self.STATUS_FAILED:
            self.is_completed = False
            self.completed_at = timezone.now()
        if self.started_at and self.completed_at:
            self.runtime_seconds = (self.completed_at - self.started_at).total_seconds()
        self.save()

    def dictify_performance(self):
        if not self.performance:
            return None
        return json.loads(self.performance)

    def dictify_meta(self):
        if not self.meta:
            return None
        return json.loads(self.meta)

    def prettify_log(self):
        return self.log.splitlines() if self.log else None

    def jsonl(self):
        return {
            'session': self.session,
            'seed': self.seed,
            'status': self.status,
            'is_completed': self.is_completed,
            'created_at': self.created_at.astimezone().isoformat(),
            'started_at': self.started_at and self.started_at.astimezone().isoformat(),
            'completed_at': self.completed_at and self.completed_at.astimezone().isoformat(),
            'performance': self.dictify_performance(),
            'pid': self.pid,
            'phase': self.phase,
            'runtime_seconds': self.runtime_seconds,
        }

    def json(self):
        return {
            'signature': self.evaluation.signature,
            'session': self.session,
            'seed': self.seed,
            'status': self.status,
            'phase': self.phase,
            'performance': self.dictify_performance(),
            'meta': self.dictify_meta(),
            'is_completed': self.is_completed,
            'created_at': self.created_at.astimezone().isoformat(),
            'started_at': self.started_at and self.started_at.astimezone().isoformat(),
            'completed_at': self.completed_at and self.completed_at.astimezone().isoformat(),
            'pid': self.pid,
            'hostname': self.hostname,
            'run_dir': self.run_dir,
            'log_path': self.log_path,
            'command': self.command,
            'error': self.error,
            'runtime_seconds': self.runtime_seconds,
        }

    def __str__(self):
        return f'{self.evaluation.signature}:{self.seed}'
