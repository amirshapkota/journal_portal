"""
URL configuration for analytics app.
Handles metrics and reports.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

# from .views import MetricsViewSet, ReportsViewSet, DashboardViewSet

router = DefaultRouter()
# router.register(r'metrics', MetricsViewSet)
# router.register(r'reports', ReportsViewSet)
# router.register(r'dashboards', DashboardViewSet)

urlpatterns = [
    path('', include(router.urls)),
    # Add custom analytics endpoints here
    # path('dashboard/', DashboardView.as_view(), name='dashboard'),
    # path('submission-stats/', SubmissionStatsView.as_view(), name='submission_stats'),
    # path('reviewer-stats/', ReviewerStatsView.as_view(), name='reviewer_stats'),
    # path('journal-performance/', JournalPerformanceView.as_view(), name='journal_performance'),
    # path('export/csv/', ExportCSVView.as_view(), name='export_csv'),
    # path('export/pdf/', ExportPDFView.as_view(), name='export_pdf'),
]