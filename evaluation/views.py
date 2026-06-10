import json

from django.core.paginator import Paginator
from django.views import View

from common.auth import require_login
from common import function, handler
from common.http import error, ok, parse_json
from evaluation.export import get_leaderboard, get_total_running_hours
from evaluation.models import Evaluation, Experiment
from evaluation.params import EvaluationParams, ExportParams


class HealthView(View):
    def get(self, request):
        return ok({'status': 'ok'})


class EvaluationView(View):
    def get(self, request, signature=None):
        if signature:
            try:
                evaluation = Evaluation.get_by_signature(signature)
            except Evaluation.DoesNotExist:
                return error('NOT_FOUND', 'Evaluation not found.', 404)
            return ok(evaluation.json())

        page = function.parse_int(
            request.GET.get('page'),
            default=1,
            minimum=1,
        )
        page_size = function.parse_int(
            request.GET.get('page_size'),
            default=EvaluationParams.LIST_PAGE_SIZE_DEFAULT,
            minimum=10,
            maximum=EvaluationParams.LIST_PAGE_SIZE_MAX,
        )
        evaluations = Evaluation.objects.all().order_by('-modified_at')
        for field_name in ['plan_name', 'data_name', 'model_name', 'task_type', 'repr_type', 'run_id']:
            value = request.GET.get(field_name)
            if value:
                evaluations = evaluations.filter(**{field_name: str(value).lower() if field_name != 'run_id' else str(value)})
        paginator = Paginator(evaluations, page_size)
        current_page = paginator.page(min(page, paginator.num_pages or 1))
        return ok(
            {
                'evaluations': [evaluation.jsonl() for evaluation in current_page],
                'page': current_page.number,
                'total_page': paginator.num_pages,
                'total': paginator.count,
            }
        )

    @require_login
    def post(self, request):
        try:
            payload = parse_json(request)
        except ValueError as exc:
            return error('BAD_JSON', str(exc), 400)
        signature = payload.get('signature')
        command = payload.get('command')
        configuration = payload.get('configuration')
        name = payload.get('name', '')
        if not signature or not command or configuration is None:
            return error('BAD_REQUEST', 'signature, command, and configuration are required.', 400)
        if isinstance(configuration, (dict, list)):
            configuration = handler.json_dumps(configuration)
        evaluation = Evaluation.create_or_get(signature, command, configuration, name=name)
        return ok(evaluation.json())

    @require_login
    def delete(self, request, signature):
        try:
            evaluation = Evaluation.get_by_signature(signature)
        except Evaluation.DoesNotExist:
            return error('NOT_FOUND', 'Evaluation not found.', 404)
        evaluation.delete()
        return ok(True)


class ExperimentView(View):
    def get(self, request, session=None):
        session = session or request.GET.get('session')
        signature = request.GET.get('signature')
        seed = function.parse_int(request.GET.get('seed'))
        try:
            experiment = Experiment.get(signature=signature, seed=seed, session=session)
        except Evaluation.DoesNotExist:
            return error('NOT_FOUND', 'Evaluation not found.', 404)
        except Experiment.DoesNotExist:
            return error('NOT_FOUND', 'Experiment not found.', 404)
        return ok(experiment.json())

    @require_login
    def post(self, request):
        try:
            payload = parse_json(request)
        except ValueError as exc:
            return error('BAD_JSON', str(exc), 400)
        signature = payload.get('signature')
        seed = int(payload.get('seed', 42))
        if not signature:
            return error('BAD_REQUEST', 'signature is required.', 400)
        try:
            evaluation = Evaluation.get_by_signature(signature)
        except Evaluation.DoesNotExist:
            return error('NOT_FOUND', 'Evaluation not found.', 404)
        experiment = Experiment.create_or_get(evaluation, seed)
        return ok(experiment.session)

    @require_login
    def put(self, request):
        try:
            payload = parse_json(request)
        except ValueError as exc:
            return error('BAD_JSON', str(exc), 400)
        session = payload.get('session')
        if not session:
            return error('BAD_REQUEST', 'session is required.', 400)
        try:
            experiment = Experiment.get_by_session(session)
        except Experiment.DoesNotExist:
            return error('NOT_FOUND', 'Experiment not found.', 404)
        meta = payload.get('meta')
        performance = payload.get('performance')
        if isinstance(meta, (dict, list)):
            meta = handler.json_dumps(meta)
        if isinstance(performance, (dict, list)):
            performance = handler.json_dumps(performance)
        experiment.update_state(
            status=payload.get('status'),
            phase=payload.get('phase'),
            log=payload.get('log'),
            meta=meta,
            performance=performance,
            error=payload.get('error'),
        )
        return ok(experiment.json())


class ExperimentRegisterView(View):
    @require_login
    def post(self, request, session):
        try:
            payload = parse_json(request)
        except ValueError as exc:
            return error('BAD_JSON', str(exc), 400)
        try:
            experiment = Experiment.get_by_session(session)
        except Experiment.DoesNotExist:
            return error('NOT_FOUND', 'Experiment not found.', 404)
        experiment.register(
            pid=payload.get('pid'),
            hostname=payload.get('hostname', ''),
            run_dir=payload.get('run_dir', ''),
            log_path=payload.get('log_path', ''),
            command=payload.get('command', ''),
            phase=payload.get('phase', ''),
        )
        return ok(experiment.json())


class LogView(View):
    def get(self, request):
        session = request.GET.get('session')
        signature = request.GET.get('signature')
        seed = function.parse_int(request.GET.get('seed'))
        try:
            experiment = Experiment.get(signature=signature, seed=seed, session=session)
        except Evaluation.DoesNotExist:
            return error('NOT_FOUND', 'Evaluation not found.', 404)
        except Experiment.DoesNotExist:
            return error('NOT_FOUND', 'Experiment not found.', 404)
        return ok(experiment.prettify_log())


class LogSummarizeView(View):
    def get(self, request):
        updated = 0
        for experiment in Experiment.objects.all():
            if experiment.started_at and experiment.completed_at:
                experiment.runtime_seconds = (experiment.completed_at - experiment.started_at).total_seconds()
                experiment.save(update_fields=['runtime_seconds'])
                updated += 1
        return ok({'updated': updated})


class LeaderboardView(View):
    def get(self, request):
        return ok(
            get_leaderboard(
                replicate=function.parse_int(request.GET.get('replicate'), default=1, minimum=1),
                metric=request.GET.get('metric', ExportParams.DEFAULT_METRIC),
                data_name=request.GET.get('data_name'),
                model_name=request.GET.get('model_name'),
                task_type=request.GET.get('task_type'),
                repr_type=request.GET.get('repr_type'),
                limit=function.parse_int(
                    request.GET.get('limit'),
                    default=ExportParams.DEFAULT_LIMIT,
                    minimum=1,
                    maximum=200,
                ),
            )
        )


class RuntimeStatsView(View):
    def get(self, request):
        return ok({'runtime_hours': get_total_running_hours()})
