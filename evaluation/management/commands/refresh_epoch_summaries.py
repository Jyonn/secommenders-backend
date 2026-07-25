from django.core.management.base import BaseCommand

from evaluation.log_parser import dumps_epoch_summary, parse_epoch_summary
from evaluation.models import Experiment


class Command(BaseCommand):
    help = 'Parse uploaded experiment logs and refresh epoch summary fields.'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='Write parsed epoch summaries to the database.')
        parser.add_argument('--limit', type=int, default=0, help='Maximum number of experiments to scan.')

    def handle(self, *args, **options):
        apply = bool(options.get('apply'))
        limit = int(options.get('limit') or 0)
        queryset = Experiment.objects.exclude(log='')
        if limit > 0:
            queryset = queryset[:limit]

        scanned = 0
        parsed = 0
        updated = 0
        for experiment in queryset.iterator():
            scanned += 1
            summary = parse_epoch_summary(experiment.log)
            if not summary:
                continue
            parsed += 1
            changes = {
                'trained_epochs': summary.get('trained_epochs'),
                'log_best_epoch': summary.get('log_best_epoch'),
                'avg_train_epoch_seconds': summary.get('avg_train_epoch_seconds'),
                'avg_eval_epoch_seconds': summary.get('avg_eval_epoch_seconds'),
                'epoch_summary': dumps_epoch_summary(summary),
            }
            if experiment.best_epoch is None and changes['log_best_epoch'] is not None:
                changes['best_epoch'] = changes['log_best_epoch']
            dirty_fields = [
                field
                for field, value in changes.items()
                if getattr(experiment, field) != value
            ]
            if not dirty_fields:
                continue
            updated += 1
            if apply:
                for field in dirty_fields:
                    setattr(experiment, field, changes[field])
                experiment.save(update_fields=dirty_fields)

        mode = 'apply' if apply else 'dry-run'
        self.stdout.write(
            f'epoch summary refresh mode={mode} scanned={scanned} parsed={parsed} updated={updated}'
        )
