import hashlib

from django.db import IntegrityError, models
from django.utils import timezone
from django.utils.crypto import get_random_string

from common import handler
from evaluation.validators import EvaluationValidator, ExperimentValidator


class EvaluationConflictError(ValueError):
    pass


class Evaluation(models.Model):
    vldt = EvaluationValidator

    signature = models.CharField(max_length=vldt.MAX_SIGNATURE_LENGTH, unique=True)
    name = models.CharField(max_length=vldt.MAX_NAME_LENGTH, blank=True)
    command_digest = models.CharField(max_length=64, unique=True, db_index=True)
    command = models.TextField()
    configuration = models.TextField()
    plan_name = models.CharField(max_length=vldt.MAX_FIELD_LENGTH, blank=True, db_index=True)
    data_name = models.CharField(max_length=vldt.MAX_FIELD_LENGTH, blank=True, db_index=True)
    model_name = models.CharField(max_length=vldt.MAX_FIELD_LENGTH, blank=True, db_index=True)
    task_type = models.CharField(max_length=vldt.MAX_FIELD_LENGTH, blank=True, db_index=True)
    repr_type = models.CharField(max_length=vldt.MAX_FIELD_LENGTH, blank=True, db_index=True)
    repr_source_model = models.CharField(max_length=vldt.MAX_FIELD_LENGTH, blank=True)
    repr_combine = models.CharField(max_length=vldt.MAX_FIELD_LENGTH, blank=True)
    sid_coder = models.CharField(max_length=vldt.MAX_FIELD_LENGTH, blank=True)
    hash_coder = models.CharField(max_length=vldt.MAX_FIELD_LENGTH, blank=True)
    run_id = models.CharField(max_length=vldt.MAX_FIELD_LENGTH, blank=True, db_index=True)
    compile_prepare_id = models.CharField(max_length=255, blank=True, db_index=True)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    @classmethod
    def create(cls, signature, command, configuration, name=''):
        evaluation = cls(
            signature=signature,
            command_digest=cls.digest_command(command),
            command=command,
            configuration=configuration,
            name=name or '',
        )
        evaluation._refresh_metadata_fields()
        evaluation.save()
        return evaluation

    @classmethod
    def create_or_get(cls, signature, command, configuration, name=''):
        command_digest = cls.digest_command(command)
        evaluation = cls.objects.filter(signature=signature).first()
        if evaluation is None:
            evaluation = cls.objects.filter(command_digest=command_digest).first()
        if evaluation is None:
            try:
                return cls.create(signature, command, configuration, name=name)
            except IntegrityError as exc:
                evaluation = (
                    cls.objects.filter(signature=signature).first()
                    or cls.objects.filter(command_digest=command_digest).first()
                )
                if evaluation is None:
                    raise EvaluationConflictError(
                        f'Unable to create evaluation signature={signature}: {exc}'
                    ) from exc

        signature_owner = cls.objects.filter(signature=signature).exclude(pk=evaluation.pk).first()
        if signature_owner is not None:
            raise EvaluationConflictError(
                f'Evaluation signature conflict: signature={signature} already belongs to '
                f'evaluation id={signature_owner.pk}, but command_digest points to id={evaluation.pk}.'
            )

        digest_owner = cls.objects.filter(command_digest=command_digest).exclude(pk=evaluation.pk).first()
        if digest_owner is not None:
            raise EvaluationConflictError(
                f'Evaluation command conflict: command_digest={command_digest} already belongs to '
                f'evaluation id={digest_owner.pk}, but signature points to id={evaluation.pk}.'
            )

        dirty = False
        if evaluation.signature != signature:
            evaluation.signature = signature
            dirty = True
        if evaluation.command_digest != command_digest:
            evaluation.command_digest = command_digest
            dirty = True
        if evaluation.configuration != configuration:
            evaluation.configuration = configuration
            dirty = True
        if evaluation.command != command:
            evaluation.command = command
            dirty = True
        if name and evaluation.name != name:
            evaluation.name = name
            dirty = True
        before = {
            'plan_name': evaluation.plan_name,
            'data_name': evaluation.data_name,
            'model_name': evaluation.model_name,
            'task_type': evaluation.task_type,
            'repr_type': evaluation.repr_type,
            'repr_source_model': evaluation.repr_source_model,
            'repr_combine': evaluation.repr_combine,
            'sid_coder': evaluation.sid_coder,
            'hash_coder': evaluation.hash_coder,
            'run_id': evaluation.run_id,
            'compile_prepare_id': evaluation.compile_prepare_id,
        }
        evaluation._refresh_metadata_fields()
        after = {
            'plan_name': evaluation.plan_name,
            'data_name': evaluation.data_name,
            'model_name': evaluation.model_name,
            'task_type': evaluation.task_type,
            'repr_type': evaluation.repr_type,
            'repr_source_model': evaluation.repr_source_model,
            'repr_combine': evaluation.repr_combine,
            'sid_coder': evaluation.sid_coder,
            'hash_coder': evaluation.hash_coder,
            'run_id': evaluation.run_id,
            'compile_prepare_id': evaluation.compile_prepare_id,
        }
        if dirty or before != after:
            try:
                evaluation.save()
            except IntegrityError as exc:
                raise EvaluationConflictError(
                    f'Unable to update evaluation signature={signature}: {exc}'
                ) from exc
        return evaluation

    @classmethod
    def get_by_signature(cls, signature):
        return cls.objects.get(signature=signature)

    @staticmethod
    def digest_command(command: str):
        return hashlib.sha256(str(command).encode('utf-8')).hexdigest()

    def prettify_configuration(self):
        if not self.configuration:
            return None
        return handler.json_loads(self.configuration)

    def _source_args(self):
        configuration = self.prettify_configuration() or {}
        return configuration.get('logical_train_args') or configuration.get('base_args') or {}

    def _refresh_metadata_fields(self):
        configuration = self.prettify_configuration() or {}
        args = self._source_args()
        self.plan_name = str(configuration.get('plan_name') or '').strip()
        self.data_name = str(args.get('data') or '').strip().lower()
        self.model_name = str(args.get('model') or '').strip().lower()
        self.task_type = str(args.get('task_type') or '').strip().lower()
        self.repr_type = str(args.get('repr_type') or '').strip().lower()
        self.repr_source_model = str(args.get('repr_source_model') or '').strip().lower()
        self.repr_combine = str(args.get('repr_combine') or '').strip().lower()
        self.sid_coder = str(args.get('sid_coder') or '').strip().lower()
        self.hash_coder = str(args.get('hash_coder') or '').strip().lower()
        self.run_id = str(configuration.get('run_id') or '').strip()
        self.compile_prepare_id = str(configuration.get('compile_prepare_id') or '').strip()

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

    def summarize_status(self):
        experiments = list(self.experiment_set.all())
        completed = sum(1 for experiment in experiments if experiment.is_completed)
        running = sum(1 for experiment in experiments if experiment.status == Experiment.STATUS_RUNNING)
        failed = sum(1 for experiment in experiments if experiment.status == Experiment.STATUS_FAILED)
        return {
            'total': len(experiments),
            'completed': completed,
            'running': running,
            'failed': failed,
        }

    def jsonl(self):
        return {
            'signature': self.signature,
            'name': self.name,
            'plan_name': self.plan_name,
            'command': self.command,
            'data_name': self.data_name,
            'model_name': self.model_name,
            'task_type': self.task_type,
            'repr_type': self.repr_type,
            'repr_source_model': self.repr_source_model,
            'repr_combine': self.repr_combine,
            'sid_coder': self.sid_coder,
            'hash_coder': self.hash_coder,
            'run_id': self.run_id,
            'compile_prepare_id': self.compile_prepare_id,
            'created_at': self.created_at.astimezone().isoformat(),
            'modified_at': self.modified_at.astimezone().isoformat(),
            'comment': self.comment,
            'status_summary': self.summarize_status(),
            'experiments': [experiment.jsonl() for experiment in self.experiment_set.all().order_by('seed', 'created_at')],
        }

    def json(self):
        return {
            'signature': self.signature,
            'name': self.name,
            'plan_name': self.plan_name,
            'command': self.command,
            'configuration': self.prettify_configuration(),
            'data_name': self.data_name,
            'model_name': self.model_name,
            'task_type': self.task_type,
            'repr_type': self.repr_type,
            'repr_source_model': self.repr_source_model,
            'repr_combine': self.repr_combine,
            'sid_coder': self.sid_coder,
            'hash_coder': self.hash_coder,
            'run_id': self.run_id,
            'compile_prepare_id': self.compile_prepare_id,
            'status_summary': self.summarize_status(),
            'performance_summary': self.prettify_performance(),
            'created_at': self.created_at.astimezone().isoformat(),
            'modified_at': self.modified_at.astimezone().isoformat(),
            'comment': self.comment,
            'experiments': [experiment.json() for experiment in self.experiment_set.all().order_by('seed', 'created_at')],
        }

    def __str__(self):
        return self.name or self.signature


class Experiment(models.Model):
    vldt = ExperimentValidator

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
    session = models.CharField(max_length=vldt.MAX_SESSION_LENGTH, unique=True)
    phase = models.CharField(max_length=vldt.MAX_PHASE_LENGTH, blank=True)
    status = models.CharField(max_length=vldt.MAX_STATUS_LENGTH, choices=STATUS_CHOICES, default=STATUS_CREATED)
    pid = models.IntegerField(null=True, blank=True)
    hostname = models.CharField(max_length=vldt.MAX_HOSTNAME_LENGTH, blank=True)
    run_dir = models.TextField(blank=True)
    log_path = models.TextField(blank=True)
    command = models.TextField(blank=True)
    log = models.TextField(blank=True)
    meta = models.TextField(blank=True)
    performance = models.TextField(blank=True)
    error = models.TextField(blank=True)
    world_size = models.IntegerField(null=True, blank=True)
    best_epoch = models.IntegerField(null=True, blank=True)
    best_valid_metric = models.FloatField(null=True, blank=True)
    main_metric = models.CharField(max_length=64, blank=True)
    test_metric_name = models.CharField(max_length=64, blank=True)
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
        experiment = cls.objects.filter(evaluation=evaluation, seed=seed).order_by('created_at', 'pk').first()
        if experiment is not None:
            return experiment
        try:
            return cls.create(evaluation, seed)
        except IntegrityError:
            experiment = cls.objects.filter(evaluation=evaluation, seed=seed).order_by('created_at', 'pk').first()
            if experiment is not None:
                return experiment
            raise

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
        self._refresh_summary_from_meta()
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
        return handler.json_loads(self.performance)

    def dictify_meta(self):
        if not self.meta:
            return None
        return handler.json_loads(self.meta)

    def _refresh_summary_from_meta(self):
        meta = self.dictify_meta() or {}
        self.world_size = meta.get('world_size')
        self.best_epoch = meta.get('best_epoch')
        self.best_valid_metric = meta.get('best_valid_metric')
        self.main_metric = str(meta.get('main_metric') or '')
        self.test_metric_name = str(meta.get('test_metric_name') or '')

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
            'world_size': self.world_size,
            'best_epoch': self.best_epoch,
            'best_valid_metric': self.best_valid_metric,
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
            'world_size': self.world_size,
            'best_epoch': self.best_epoch,
            'best_valid_metric': self.best_valid_metric,
            'main_metric': self.main_metric,
            'test_metric_name': self.test_metric_name,
        }

    def __str__(self):
        return f'{self.evaluation.signature}:{self.seed}'
