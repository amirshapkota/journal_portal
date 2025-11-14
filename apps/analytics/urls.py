"""
URL configuration for analytics app.
Handles metrics and reports.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    AnalyticsDashboardView,
    SubmissionAnalyticsView,
    ReviewerAnalyticsView,
    JournalAnalyticsView,
    UserAnalyticsView,
    MyAnalyticsView,
)

router = DefaultRouter()

urlpatterns = [
    path('', include(router.urls)),
    
    # Dashboard analytics (Admin/Editor only)
    path('dashboard/', AnalyticsDashboardView.as_view(), name='analytics-dashboard'),
    path('submissions/', SubmissionAnalyticsView.as_view(), name='analytics-submissions'),
    path('reviewers/', ReviewerAnalyticsView.as_view(), name='analytics-reviewers'),
    path('journals/', JournalAnalyticsView.as_view(), name='analytics-journals'),
    path('users/', UserAnalyticsView.as_view(), name='analytics-users'),
    
    # Personal analytics (All authenticated users)
    path('my-analytics/', MyAnalyticsView.as_view(), name='my-analytics'),
]