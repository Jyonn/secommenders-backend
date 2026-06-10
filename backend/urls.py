from django.urls import path

from evaluation.views import (
    EvaluationCollectionView,
    EvaluationDetailView,
    ExperimentCollectionView,
    ExperimentDetailView,
    ExperimentRegisterView,
    ExportView,
    HealthView,
    LogSummarizeView,
    LogView,
)


urlpatterns = [
    path('healthz', HealthView.as_view(), name='health'),
    path('evaluations/', EvaluationCollectionView.as_view(), name='evaluation-list'),
    path('evaluations/export', ExportView.as_view(), name='evaluation-export'),
    path('evaluations/<str:signature>', EvaluationDetailView.as_view(), name='evaluation-detail'),
    path('experiments/', ExperimentCollectionView.as_view(), name='experiment-list'),
    path('experiments/log', LogView.as_view(), name='experiment-log'),
    path('experiments/<str:session>', ExperimentDetailView.as_view(), name='experiment-detail'),
    path('experiments/<str:session>/register', ExperimentRegisterView.as_view(), name='experiment-register'),
    path('log-summarize', LogSummarizeView.as_view(), name='log-summarize'),
]
