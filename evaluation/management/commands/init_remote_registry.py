import hashlib
import json
import re
import sys
from collections import defaultdict
from copy import deepcopy
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from common import handler
from evaluation.models import Evaluation


EVALUATION_SIGNATURE_VERSION = 'evaluation.v2'
REPORT_RUNTIME_ARG_KEYS = {
    'batch_size',
    'accumulate_batch',
    'device',
    'num_gpus',
    'valid_only',
    'test_only',
    'load_ckpt',
    'overwrite',
    'code_beam_chunk_size',
}
LEGACY_RUN_HASH_RE = re.compile(r'__h([0-9a-fA-F]{6,64})$')


def short_config_hash(payload: dict, length: int = 16):
    serialized = json.dumps(payload, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(serialized.encode('utf-8')).hexdigest()[:length]


def json_loads_or_none(text: str):
    if not text:
        return None
    try:
        return handler.json_loads(text)
    except Exception:
        return None


def canonical_report_args(args: dict, *, effective_batch_size: int):
    canonical = deepcopy(args)
    for key in REPORT_RUNTIME_ARG_KEYS:
        canonical.pop(key, None)
    canonical['effective_batch_size'] = int(effective_batch_size)
    return canonical


def effective_batch_from_args(args: dict):
    if args.get('effective_batch_size') is not None:
        return int(args['effective_batch_size'])
    batch_size = args.get('batch_size')
    accumulate_batch = args.get('accumulate_batch')
    if batch_size is not None and accumulate_batch is not None:
        return int(batch_size) * int(accumulate_batch)
    return None


def legacy_hash_from_run_id(value: str):
    match = LEGACY_RUN_HASH_RE.search(str(value or ''))
    if not match:
        return None
    return f'legacy:{match.group(1).lower()}'


def find_algorithm_root(option_value: str | None):
    candidates = []
    if option_value:
        candidates.append(Path(option_value).expanduser())
    candidates.extend(
        [
            Path('../secommenders-algorithm'),
            Path('../Secommenders'),
            Path('~/Secommenders').expanduser(),
            Path('~/secommenders-algorithm').expanduser(),
            Path('/home/data4/qijiong/Code/Secommenders'),
            Path('/root/autodl-tmp/Secommenders'),
        ]
    )
    for candidate in candidates:
        candidate = candidate.resolve()
        if (candidate / 'config' / 'trainer.yaml').exists() and (candidate / 'utils' / 'artifact_identity.py').exists():
            return candidate
    return None


class AlgorithmSigner:
    def __init__(self, algorithm_root: Path | None):
        self.algorithm_root = algorithm_root
        self.available = False
        self.error = ''
        if algorithm_root is None:
            self.error = 'algorithm root not found'
            return
        try:
            sys.path.insert(0, str(algorithm_root))
            from utils.artifact_identity import trained_signature_from_config

            self.trained_signature_from_config = trained_signature_from_config
            self.available = True
        except Exception as exc:
            self.error = repr(exc)

    def sign(self, args: dict):
        if not self.available:
            return None
        return self.trained_signature_from_config(dict(args))


def first_experiment_meta_config(evaluation):
    for experiment in evaluation.experiment_set.all().order_by('created_at', 'id'):
        meta = json_loads_or_none(experiment.meta)
        if isinstance(meta, dict) and isinstance(meta.get('config'), dict):
            return meta['config']
    return None


def canonicalize_signature_payload(configuration: dict, evaluation, signer: AlgorithmSigner):
    payload = configuration.get('signature_payload')
    if not isinstance(payload, dict):
        payload = configuration

    train_args = (
        payload.get('logical_train_args')
        or configuration.get('logical_train_args')
        or first_experiment_meta_config(evaluation)
        or configuration.get('base_args')
        or {}
    )
    effective_batch_size = (
        payload.get('effective_batch_size')
        or configuration.get('effective_batch_size')
        or effective_batch_from_args(train_args)
    )
    trained_signature = payload.get('trained_signature') or configuration.get('trained_signature')
    if not trained_signature and train_args:
        trained_signature = signer.sign(train_args)
    if not trained_signature:
        trained_signature = legacy_hash_from_run_id(configuration.get('run_id') or evaluation.run_id)

    if effective_batch_size is None and train_args:
        effective_batch_size = effective_batch_from_args(train_args)

    if effective_batch_size is None or not trained_signature:
        return None

    canonical = {
        'schema_version': EVALUATION_SIGNATURE_VERSION,
        'effective_batch_size': int(effective_batch_size),
        'logical_train_args': canonical_report_args(train_args, effective_batch_size=int(effective_batch_size)),
        'trained_signature': trained_signature,
    }
    return canonical


def normalized_configuration(configuration: dict, signature_payload: dict):
    updated = dict(configuration)
    updated['signature_payload'] = signature_payload
    return updated


class Command(BaseCommand):
    help = 'Recompute and regroup remote evaluations by the current SIGN payload.'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='Write database changes. Default is dry-run.')
        parser.add_argument('--signature', help='Only process one current evaluation signature.')
        parser.add_argument('--delete-empty', action='store_true', help='Delete source evaluations after moving experiments.')
        parser.add_argument('--algorithm-root', help='Path to secommenders-algorithm for exact trained SIGN recomputation.')

    def _collect(self, signature: str | None, signer: AlgorithmSigner):
        queryset = Evaluation.objects.all().order_by('created_at', 'id')
        if signature:
            queryset = queryset.filter(signature=signature)

        resolved = []
        skipped = []
        for evaluation in queryset:
            configuration = json_loads_or_none(evaluation.configuration)
            if not isinstance(configuration, dict):
                skipped.append((evaluation, 'configuration is not JSON object'))
                continue
            signature_payload = canonicalize_signature_payload(configuration, evaluation, signer)
            if not signature_payload:
                skipped.append((evaluation, 'missing usable signature_payload'))
                continue
            target_signature = short_config_hash(signature_payload, length=16)
            target_configuration = normalized_configuration(configuration, signature_payload)
            resolved.append(
                {
                    'evaluation': evaluation,
                    'target_signature': target_signature,
                    'target_configuration': target_configuration,
                    'target_configuration_text': handler.json_dumps(target_configuration),
                    'signature_payload': signature_payload,
                }
            )
        return resolved, skipped

    @staticmethod
    def _choose_keeper(records: list[dict], target_signature: str):
        exact = [record for record in records if record['evaluation'].signature == target_signature]
        if exact:
            return exact[0]
        return records[0]

    def _plan(self, resolved: list[dict]):
        by_target = defaultdict(list)
        for record in resolved:
            by_target[record['target_signature']].append(record)
        conflicts = []
        for target_signature, records in by_target.items():
            record_ids = [record['evaluation'].id for record in records]
            external = Evaluation.objects.filter(signature=target_signature).exclude(id__in=record_ids).first()
            if external is not None:
                conflicts.append((target_signature, external))
        return by_target, conflicts

    def _print_plan(self, by_target, skipped, conflicts, *, apply: bool):
        mode = 'apply' if apply else 'dry-run'
        self.stdout.write(
            f'remote registry init mode={mode} targets={len(by_target)} resolved='
            f'{sum(len(records) for records in by_target.values())} skipped={len(skipped)} conflicts={len(conflicts)}'
        )
        for target_signature, records in sorted(by_target.items()):
            keeper = self._choose_keeper(records, target_signature)['evaluation']
            experiment_count = sum(record['evaluation'].experiment_set.count() for record in records)
            action = 'keep' if keeper.signature == target_signature else 'rename'
            self.stdout.write(
                f'  target {target_signature} action={action} keeper={keeper.signature} '
                f'evaluations={len(records)} experiments={experiment_count}'
            )
            for record in records:
                evaluation = record['evaluation']
                marker = '*' if evaluation.id == keeper.id else '-'
                if evaluation.signature == target_signature and len(records) == 1:
                    detail = 'refresh'
                elif evaluation.id == keeper.id:
                    detail = 'keeper'
                else:
                    detail = 'move-experiments'
                self.stdout.write(
                    f'    {marker} {evaluation.signature} -> {target_signature} '
                    f'{detail} experiments={evaluation.experiment_set.count()} name={evaluation.name or "-"}'
                )
        for evaluation, reason in skipped:
            self.stdout.write(f'  skipped {evaluation.signature}: {reason}')
        for target_signature, external in conflicts:
            self.stdout.write(
                f'  conflict target {target_signature}: already occupied by external evaluation '
                f'{external.signature} id={external.id}'
            )

    def _apply_target(self, target_signature: str, records: list[dict], *, delete_empty: bool):
        keeper_record = self._choose_keeper(records, target_signature)
        keeper = keeper_record['evaluation']

        if keeper.signature != target_signature:
            keeper.signature = target_signature
        if keeper.configuration != keeper_record['target_configuration_text']:
            keeper.configuration = keeper_record['target_configuration_text']
        keeper._refresh_metadata_fields()
        keeper.save()

        for record in records:
            source = record['evaluation']
            if source.id == keeper.id:
                continue
            source.experiment_set.update(evaluation=keeper)
            if delete_empty:
                source.delete()
            else:
                source.comment = (source.comment + '\n' if source.comment else '') + (
                    f'migrated to {target_signature} by init_remote_registry'
                )
                source.save(update_fields=['comment', 'modified_at'])

    @transaction.atomic
    def _apply(self, by_target, *, delete_empty: bool):
        for target_signature, records in by_target.items():
            self._apply_target(target_signature, records, delete_empty=delete_empty)

    def handle(self, *args, **options):
        algorithm_root = find_algorithm_root(options.get('algorithm_root'))
        signer = AlgorithmSigner(algorithm_root)
        if signer.available:
            self.stdout.write(f'algorithm signer enabled root={algorithm_root}')
        else:
            self.stdout.write(f'algorithm signer unavailable: {signer.error}; falling back to legacy run_id hashes')

        resolved, skipped = self._collect(options.get('signature'), signer)
        by_target, conflicts = self._plan(resolved)
        self._print_plan(by_target, skipped, conflicts, apply=options['apply'])
        if conflicts:
            raise SystemExit('remote registry init has conflicts; resolve them before applying')
        if not options['apply']:
            return
        self._apply(by_target, delete_empty=options['delete_empty'])
        self.stdout.write(self.style.SUCCESS('remote registry init complete'))
