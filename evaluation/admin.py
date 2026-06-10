from django.contrib import admin

from evaluation.models import Evaluation, Experiment


class ExperimentInline(admin.TabularInline):
    model = Experiment
    extra = 0
    readonly_fields = ('session', 'seed', 'status', 'pid', 'hostname', 'created_at', 'started_at', 'completed_at')


@admin.register(Evaluation)
class EvaluationAdmin(admin.ModelAdmin):
    list_display = ('signature', 'name', 'created_at', 'modified_at')
    search_fields = ('signature', 'name', 'command')
    inlines = [ExperimentInline]


@admin.register(Experiment)
class ExperimentAdmin(admin.ModelAdmin):
    list_display = ('session', 'evaluation', 'seed', 'status', 'is_completed', 'created_at', 'completed_at')
    search_fields = ('session', 'evaluation__signature', 'hostname', 'run_dir')
    list_filter = ('status', 'is_completed')
