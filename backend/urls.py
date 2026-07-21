from django.urls import path

from evaluation.views import (
    EvaluationOptionsView,
    EvaluationView,
    ExperimentView,
    ExperimentRegisterView,
    HealthView,
    LeaderboardView,
    LogSummarizeView,
    LogView,
    RuntimeStatsView,
)


urlpatterns = [
    path('healthz', HealthView.as_view(), name='health'),
    path('evaluations/', EvaluationView.as_view(), name='evaluation-list'),
    path('evaluations/options', EvaluationOptionsView.as_view(), name='evaluation-options'),
    path('evaluations/leaderboard', LeaderboardView.as_view(), name='evaluation-leaderboard'),
    path('evaluations/<str:signature>', EvaluationView.as_view(), name='evaluation-detail'),
    path('experiments/', ExperimentView.as_view(), name='experiment-list'),
    path('experiments/log', LogView.as_view(), name='experiment-log'),
    path('experiments/<str:session>', ExperimentView.as_view(), name='experiment-detail'),
    path('experiments/<str:session>/register', ExperimentRegisterView.as_view(), name='experiment-register'),
    path('log-summarize', LogSummarizeView.as_view(), name='log-summarize'),
    path('stats/runtime-hours', RuntimeStatsView.as_view(), name='runtime-hours'),
]
